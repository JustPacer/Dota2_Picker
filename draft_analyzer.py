import itertools
import database

# Smoothing constant for Bayesian win rate smoothing
SMOOTH_CONST = 15

def assign_roles_partial(heroes):
    """
    Given a list of hero IDs (length 0 to 5), assigns them to a subset of positions 1-5
    that maximizes the sum of their historical playing frequencies in those positions.
    Returns a dictionary of hero_id -> position (1-5).
    """
    if not heroes:
        return {}
    
    k = len(heroes)
    # Fetch role weights (games counts) for each hero
    weights = {h: database.get_role_weights(h) for h in heroes}
    
    best_assignment = None
    best_weight = -1
    
    # Try all permutations of size k from [1, 2, 3, 4, 5]
    for pos_combination in itertools.permutations([1, 2, 3, 4, 5], k):
        current_weight = 0
        for i, pos in enumerate(pos_combination):
            h_id = heroes[i]
            h_weights = weights[h_id]
            total_games = sum(h_weights.values())
            if total_games > 0:
                # Use percentage to normalize popularity
                pct = h_weights.get(pos, 0) / total_games
            else:
                pct = 0
            current_weight += pct
            
        if current_weight > best_weight:
            best_weight = current_weight
            best_assignment = {heroes[i]: pos_combination[i] for i in range(k)}
            
    return best_assignment

def assign_roles_with_constraint(heroes, constraint):
    """
    Given a list of hero IDs, assigns them to a subset of positions 1-5
    maximizing their playing frequencies, subject to constraints (hero_id -> forced_role).
    """
    if not heroes:
        return {}
        
    k = len(heroes)
    weights = {h: database.get_role_weights(h) for h in heroes}
    
    best_assignment = None
    best_weight = -1
    
    # Try all permutations of size k from [1, 2, 3, 4, 5]
    for pos_combination in itertools.permutations([1, 2, 3, 4, 5], k):
        # Validate constraints
        valid = True
        for i, pos in enumerate(pos_combination):
            h_id = heroes[i]
            if h_id in constraint and constraint[h_id] != pos:
                valid = False
                break
        if not valid:
            continue
            
        current_weight = 0
        for i, pos in enumerate(pos_combination):
            h_id = heroes[i]
            h_weights = weights[h_id]
            total_games = sum(h_weights.values())
            if total_games > 0:
                pct = h_weights.get(pos, 0) / total_games
            else:
                pct = 0
            current_weight += pct
            
        if current_weight > best_weight:
            best_weight = current_weight
            best_assignment = {heroes[i]: pos_combination[i] for i in range(k)}
            
    return best_assignment


def get_smoothed_matchup_adv(hero_id, opponent_id, hero_base_wr):
    """
    Calculates the smoothed matchup advantage of hero_id vs opponent_id.
    smoothed_wr = (wins + C * base_wr) / (games + C)
    advantage = smoothed_wr - base_wr
    """
    matchups = database.get_matchups_for_hero(hero_id)
    games, wins = matchups.get(opponent_id, (0, 0))
    
    # Apply Bayesian smoothing
    smoothed_wr = (wins + SMOOTH_CONST * hero_base_wr) / (games + SMOOTH_CONST)
    return smoothed_wr - hero_base_wr

def get_smoothed_synergy(hero_id1, hero_id2, base_wr1, base_wr2):
    """
    Calculates the smoothed synergy between hero_id1 and hero_id2 on the same team.
    smoothed_wr = (wins + C * avg_base) / (games + C)
    synergy = smoothed_wr - avg_base
    """
    synergies = database.get_synergies_for_hero(hero_id1)
    games, wins = synergies.get(hero_id2, (0, 0))
    
    avg_base = (base_wr1 + base_wr2) / 2
    
    # Apply Bayesian smoothing
    smoothed_wr = (wins + SMOOTH_CONST * avg_base) / (games + SMOOTH_CONST)
    return smoothed_wr - avg_base

def analyze_draft(radiant_heroes, dire_heroes, custom_roles_radiant=None, custom_roles_dire=None):
    """
    Analyzes the draft between Radiant and Dire.
    radiant_heroes, dire_heroes: lists of hero IDs.
    custom_roles_radiant, custom_roles_dire: optional manual role assignments (hero_id -> 1..5).
    
    Returns a dictionary of analysis results:
      - radiant_win_prob: float (0.0 to 1.0)
      - radiant_base_wr, dire_base_wr: float
      - matchups: list of dicts with keys (rad_id, dire_id, adv)
      - radiant_synergies: list of dicts with keys (hero_id1, hero_id2, synergy)
      - dire_synergies: list of dicts with keys (hero_id1, hero_id2, synergy)
      - laning: dict containing predictions for each lane
    """
    # 1. Fetch base stats for picked heroes
    heroes_pool = {h['id']: h for h in database.get_all_heroes()}
    
    r_base_wrs = [heroes_pool[h]['base_win_rate'] for h in radiant_heroes if h in heroes_pool]
    d_base_wrs = [heroes_pool[h]['base_win_rate'] for h in dire_heroes if h in heroes_pool]
    
    r_avg_base = sum(r_base_wrs) / len(r_base_wrs) if r_base_wrs else 0.50
    d_avg_base = sum(d_base_wrs) / len(d_base_wrs) if d_base_wrs else 0.50
    
    base_diff = r_avg_base - d_avg_base
    
    # 2. Matchup analysis
    matchups_list = []
    total_matchup_adv = 0
    for r_id in radiant_heroes:
        if r_id not in heroes_pool:
            continue
        r_base = heroes_pool[r_id]['base_win_rate']
        for d_id in dire_heroes:
            if d_id not in heroes_pool:
                continue
            adv = get_smoothed_matchup_adv(r_id, d_id, r_base)
            total_matchup_adv += adv
            matchups_list.append({
                'rad_id': r_id,
                'dire_id': d_id,
                'adv': adv
            })
            
    # 3. Synergy analysis
    radiant_syns = []
    total_rad_syn = 0
    for h1, h2 in itertools.combinations(radiant_heroes, 2):
        if h1 not in heroes_pool or h2 not in heroes_pool:
            continue
        syn = get_smoothed_synergy(h1, h2, heroes_pool[h1]['base_win_rate'], heroes_pool[h2]['base_win_rate'])
        total_rad_syn += syn
        # Highlight if synergy is significant
        radiant_syns.append({
            'hero_id1': h1,
            'hero_id2': h2,
            'synergy': syn
        })
        
    dire_syns = []
    total_dire_syn = 0
    for h1, h2 in itertools.combinations(dire_heroes, 2):
        if h1 not in heroes_pool or h2 not in heroes_pool:
            continue
        syn = get_smoothed_synergy(h1, h2, heroes_pool[h1]['base_win_rate'], heroes_pool[h2]['base_win_rate'])
        total_dire_syn += syn
        dire_syns.append({
            'hero_id1': h1,
            'hero_id2': h2,
            'synergy': syn
        })
        
    # 4. Draft Win Probability Formula
    # Dampen the advantages to keep predictions in a realistic 35%-65% range.
    # TotalAdv = BaseDiff + 0.1 * MatchupAdv + 0.15 * (RadSyn - DireSyn)
    total_adv = base_diff + 0.1 * total_matchup_adv + 0.15 * (total_rad_syn - total_dire_syn)
    radiant_win_prob_unclipped = 0.50 + total_adv
    radiant_win_prob = max(0.15, min(0.85, radiant_win_prob_unclipped)) # Clip final display between 15% and 85%
    
    # 5. Role & Lane analysis
    r_roles = custom_roles_radiant or assign_roles_partial(radiant_heroes)
    d_roles = custom_roles_dire or assign_roles_partial(dire_heroes)
    
    # Lanes layout:
    # Lane 1 (Radiant Offlane vs Dire Safelane): Radiant Pos 3/4, Dire Pos 1/5
    # Lane 2 (Midlane): Radiant Pos 2, Dire Pos 2
    # Lane 3 (Radiant Safelane vs Dire Offlane): Radiant Pos 1/5, Dire Pos 3/4
    
    # Function to get smoothed lane win rate for a hero in lane L
    def get_lane_wr(h_id, L):
        stats = database.get_lane_stats(h_id)
        games, wins = stats.get(L, (0, 0))
        # smoothed lane win rate (base default is 50%)
        return (wins + SMOOTH_CONST * 0.50) / (games + SMOOTH_CONST)
        
    # Map heroes to lanes
    rad_by_lane = {1: [], 2: [], 3: []}
    for h_id, pos in r_roles.items():
        if pos in [1, 5]:
            rad_by_lane[3].append(h_id)
        elif pos == 2:
            rad_by_lane[2].append(h_id)
        elif pos in [3, 4]:
            rad_by_lane[1].append(h_id)
            
    dire_by_lane = {1: [], 2: [], 3: []}
    for h_id, pos in d_roles.items():
        if pos in [1, 5]:
            # Dire Safelane is lane 1
            dire_by_lane[1].append(h_id)
        elif pos == 2:
            dire_by_lane[2].append(h_id)
        elif pos in [3, 4]:
            # Dire Offlane is lane 3
            dire_by_lane[3].append(h_id)
            
    # Calculate lane probabilities
    lane_predictions = {}
    
    # Lane 1: Radiant Off (3,4) vs Dire Safe (1,5)
    r_lane1_wrs = [get_lane_wr(h, 1) for h in rad_by_lane[1]]
    d_lane1_wrs = [get_lane_wr(h, 1) for h in dire_by_lane[1]]
    r1 = sum(r_lane1_wrs) / len(r_lane1_wrs) if r_lane1_wrs else 0.50
    d1 = sum(d_lane1_wrs) / len(d_lane1_wrs) if d_lane1_wrs else 0.50
    lane_predictions[1] = {
        'radiant_heroes': rad_by_lane[1],
        'dire_heroes': dire_by_lane[1],
        'radiant_win_prob': max(0.20, min(0.80, 0.50 + (r1 - d1))),
        'radiant_score': r1,
        'dire_score': d1
    }
    
    # Lane 2: Radiant Mid (2) vs Dire Mid (2)
    r_lane2_wrs = [get_lane_wr(h, 2) for h in rad_by_lane[2]]
    d_lane2_wrs = [get_lane_wr(h, 2) for h in dire_by_lane[2]]
    r2 = sum(r_lane2_wrs) / len(r_lane2_wrs) if r_lane2_wrs else 0.50
    d2 = sum(d_lane2_wrs) / len(d_lane2_wrs) if d_lane2_wrs else 0.50
    lane_predictions[2] = {
        'radiant_heroes': rad_by_lane[2],
        'dire_heroes': dire_by_lane[2],
        'radiant_win_prob': max(0.20, min(0.80, 0.50 + (r2 - d2))),
        'radiant_score': r2,
        'dire_score': d2
    }
    
    # Lane 3: Radiant Safe (1,5) vs Dire Off (3,4)
    r_lane3_wrs = [get_lane_wr(h, 3) for h in rad_by_lane[3]]
    d_lane3_wrs = [get_lane_wr(h, 3) for h in dire_by_lane[3]]
    r3 = sum(r_lane3_wrs) / len(r_lane3_wrs) if r_lane3_wrs else 0.50
    d3 = sum(d_lane3_wrs) / len(d_lane3_wrs) if d_lane3_wrs else 0.50
    lane_predictions[3] = {
        'radiant_heroes': rad_by_lane[3],
        'dire_heroes': dire_by_lane[3],
        'radiant_win_prob': max(0.20, min(0.80, 0.50 + (r3 - d3))),
        'radiant_score': r3,
        'dire_score': d3
    }
    
    return {
        'radiant_win_prob': radiant_win_prob,
        'radiant_win_prob_unclipped': radiant_win_prob_unclipped,
        'radiant_base_wr': r_avg_base,
        'dire_base_wr': d_avg_base,
        'matchups': matchups_list,
        'radiant_synergies': radiant_syns,
        'dire_synergies': dire_syns,
        'lanes': lane_predictions,
        'radiant_roles': r_roles,
        'dire_roles': d_roles
    }

def suggest_best_pick(team_heroes, opponent_heroes, role_to_fill, is_radiant=True):
    """
    Suggests the top 5 heroes to pick for `team_heroes` on position `role_to_fill`.
    is_radiant: True if suggesting for Radiant, False for Dire.
    """
    all_heroes = database.get_all_heroes()
    taken_heroes = set(team_heroes + opponent_heroes)
    
    suggestions = []
    
    for h in all_heroes:
        h_id = h['id']
        if h_id in taken_heroes:
            continue
            
        # Try putting this hero in the draft
        if is_radiant:
            temp_rad = team_heroes + [h_id]
            temp_dire = opponent_heroes
            custom_roles = assign_roles_with_constraint(temp_rad, {h_id: role_to_fill})
            res = analyze_draft(temp_rad, temp_dire, custom_roles_radiant=custom_roles)
            win_prob = res['radiant_win_prob']
            win_prob_unclipped = res['radiant_win_prob_unclipped']
        else:
            temp_rad = opponent_heroes
            temp_dire = team_heroes + [h_id]
            custom_roles = assign_roles_with_constraint(temp_dire, {h_id: role_to_fill})
            res = analyze_draft(temp_rad, temp_dire, custom_roles_dire=custom_roles)
            win_prob = 1.0 - res['radiant_win_prob'] # Win probability for Dire
            win_prob_unclipped = 1.0 - res['radiant_win_prob_unclipped']
            
        suggestions.append({
            'hero_id': h_id,
            'localized_name': h['localized_name'],
            'innate_name': h['innate_name'],
            'base_win_rate': h['base_win_rate'],
            'win_prob': win_prob,
            'win_prob_unclipped': win_prob_unclipped
        })
        
    # Sort suggestions by unclipped win probability descending so we don't have tie breaking issues
    suggestions.sort(key=lambda x: x['win_prob_unclipped'], reverse=True)
    return suggestions[:5]
