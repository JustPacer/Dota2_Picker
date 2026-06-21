import streamlit as st
import database
import draft_analyzer

# Set page config
st.set_page_config(
    page_title="Dota 2 Draft Analyzer (Patch 7.41d)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dota 2 dark aesthetic and rich visuals
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0d0f12;
        color: #e4e6eb;
    }
    
    /* Sleek card container */
    .metric-card {
        background-color: rgba(27, 30, 34, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Radiant styled header */
    .radiant-header {
        color: #39e3a6 !important;
        text-shadow: 0 0 10px rgba(57, 227, 166, 0.3);
        font-weight: 700;
        font-size: 1.5rem;
        margin-bottom: 10px;
        border-bottom: 2px solid rgba(57, 227, 166, 0.2);
        padding-bottom: 5px;
    }
    
    /* Dire styled header */
    .dire-header {
        color: #ff4d6d !important;
        text-shadow: 0 0 10px rgba(255, 77, 109, 0.3);
        font-weight: 700;
        font-size: 1.5rem;
        margin-bottom: 10px;
        border-bottom: 2px solid rgba(255, 77, 109, 0.2);
        padding-bottom: 5px;
    }
    
    /* Innate ability badge */
    .innate-badge {
        background-color: rgba(233, 196, 106, 0.15);
        border: 1px solid rgba(233, 196, 106, 0.4);
        color: #e9c46a;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin-top: 5px;
    }
    
    /* Info text for innates */
    .innate-desc {
        font-size: 0.85rem;
        color: #c9ada7;
        margin-top: 3px;
        font-style: italic;
    }
    
    /* Win rate progress bar text */
    .winrate-pct {
        font-size: 2rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 5px;
    }
    
    /* Laning panel */
    .lane-panel {
        background-color: rgba(33, 37, 41, 0.9);
        border-left: 4px solid #f4a261;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    /* Synergy panel */
    .synergy-panel {
        background-color: rgba(42, 157, 143, 0.15);
        border: 1px dashed rgba(42, 157, 143, 0.5);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
    }
    
    /* Matchup panel */
    .matchup-panel {
        background-color: rgba(230, 57, 70, 0.1);
        border: 1px dashed rgba(230, 57, 70, 0.3);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 1. Fetch data from cache
heroes = database.get_all_heroes()
if not heroes:
    st.error("No hero cache found! Please run the data importer `python load_data.py` first.")
    st.stop()

# Helper dictionaries
hero_name_to_id = {h['localized_name']: h['id'] for h in heroes}
hero_id_to_name = {h['id']: h['localized_name'] for h in heroes}
hero_id_to_obj = {h['id']: h for h in heroes}

# Positions names
POSITIONS = {
    1: "Pos 1: Safelane Carry",
    2: "Pos 2: Midlane Core",
    3: "Pos 3: Offlane Core",
    4: "Pos 4: Soft Support",
    5: "Pos 5: Hard Support"
}

# 2. Setup state
if 'radiant_picks' not in st.session_state:
    st.session_state['radiant_picks'] = []
if 'dire_picks' not in st.session_state:
    st.session_state['dire_picks'] = []
if 'radiant_roles' not in st.session_state:
    st.session_state['radiant_roles'] = {}
if 'dire_roles' not in st.session_state:
    st.session_state['dire_roles'] = {}

# Page Title
st.title("🛡️ Dota 2 Draft Analyzer")
st.caption("Updated for Patch 7.41d (Aspects Removed | Innate Abilities Kept)")

# Column layout for pickers
col_pick_rad, col_pick_dire = st.columns(2)

with col_pick_rad:
    st.markdown('<div class="radiant-header">Radiant Picks</div>', unsafe_allow_html=True)
    # Filter out heroes picked on Dire
    available_rad = [h['localized_name'] for h in heroes if h['id'] not in st.session_state['dire_picks']]
    rad_selections = st.multiselect(
        "Select up to 5 heroes for Radiant",
        options=available_rad,
        default=[hero_id_to_name[h] for h in st.session_state['radiant_picks'] if h in hero_id_to_name],
        max_selections=5,
        key="rad_multiselect"
    )
    # Update picks state
    new_rad_picks = [hero_name_to_id[name] for name in rad_selections]
    if new_rad_picks != st.session_state['radiant_picks']:
        st.session_state['radiant_picks'] = new_rad_picks
        # Run role fixer automatically for the new set of heroes
        st.session_state['radiant_roles'] = draft_analyzer.assign_roles_partial(new_rad_picks)

with col_pick_dire:
    st.markdown('<div class="dire-header">Dire Picks</div>', unsafe_allow_html=True)
    # Filter out heroes picked on Radiant
    available_dire = [h['localized_name'] for h in heroes if h['id'] not in st.session_state['radiant_picks']]
    dire_selections = st.multiselect(
        "Select up to 5 heroes for Dire",
        options=available_dire,
        default=[hero_id_to_name[h] for h in st.session_state['dire_picks'] if h in hero_id_to_name],
        max_selections=5,
        key="dire_multiselect"
    )
    # Update picks state
    new_dire_picks = [hero_name_to_id[name] for name in dire_selections]
    if new_dire_picks != st.session_state['dire_picks']:
        st.session_state['dire_picks'] = new_dire_picks
        # Run role fixer automatically for the new set of heroes
        st.session_state['dire_roles'] = draft_analyzer.assign_roles_partial(new_dire_picks)


# Role swapping logic
def swap_roles(team_key, p_idx, selected_hero_id):
    roles_dict = st.session_state[team_key]
    
    # Find who is currently in P=p_idx
    old_hero_id = None
    for h_id, p in roles_dict.items():
        if p == p_idx:
            old_hero_id = h_id
            break
            
    # Find what position selected_hero_id currently has
    old_pos = roles_dict[selected_hero_id]
    
    # Swap them
    if old_hero_id is not None:
        roles_dict[old_hero_id] = old_pos
    roles_dict[selected_hero_id] = p_idx
    
    st.session_state[team_key] = roles_dict

# Perform draft analysis
rad_picks = st.session_state['radiant_picks']
dire_picks = st.session_state['dire_picks']

analysis = draft_analyzer.analyze_draft(
    rad_picks, 
    dire_picks, 
    custom_roles_radiant=st.session_state['radiant_roles'], 
    custom_roles_dire=st.session_state['dire_roles']
)

# Render main tabs
tab_prediction, tab_roles, tab_lanes, tab_details, tab_suggestions = st.tabs([
    "📊 Win Prediction", 
    "🔄 Role Fixer", 
    "⚔️ Laning Analysis", 
    "📈 Duos & Counters", 
    "💡 Suggest Best Pick"
])

# Tab 1: Win Prediction
with tab_prediction:
    st.markdown("### Overall Draft Win Probability")
    
    prob_rad = analysis['radiant_win_prob']
    prob_dire = 1.0 - prob_rad
    
    # Radiant vs Dire color bar
    st.markdown(f"""
    <div class="winrate-pct">
        <span style="color:#39e3a6">{prob_rad*100:.1f}%</span> 
        <span style="color:#777; font-size:1.2rem;">vs</span> 
        <span style="color:#ff4d6d">{prob_dire*100:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Custom colored progress bar
    st.progress(float(prob_rad))
    
    st.markdown("---")
    
    # Quick Summary Cards
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("Base Stats Advantage")
        base_diff = (analysis['radiant_base_wr'] - analysis['dire_base_wr']) * 100
        if base_diff > 0:
            st.markdown(f"Radiant has a raw winrate advantage of **+{base_diff:.2f}%** based on solo winrates.")
        elif base_diff < 0:
            st.markdown(f"Dire has a raw winrate advantage of **+{abs(base_diff):.2f}%** based on solo winrates.")
        else:
            st.markdown("Both teams are equal on base hero winrates.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_stat2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("Synergy Breakdown")
        rad_syn_sum = sum(s['synergy'] for s in analysis['radiant_synergies']) * 100
        dire_syn_sum = sum(s['synergy'] for s in analysis['dire_synergies']) * 100
        st.write(f"Radiant Synergy Sum: **+{rad_syn_sum:.2f}%**")
        st.write(f"Dire Synergy Sum: **+{dire_syn_sum:.2f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_stat3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("Matchup Counters")
        rad_m_adv = sum(m['adv'] for m in analysis['matchups']) * 100
        if rad_m_adv > 0:
            st.markdown(f"Radiant heroes counter Dire heroes on average by **+{rad_m_adv:.2f}%**.")
        elif rad_m_adv < 0:
            st.markdown(f"Dire heroes counter Radiant heroes on average by **+{abs(rad_m_adv):.2f}%**.")
        else:
            st.markdown("No active matchups calculated (needs heroes selected on both sides).")
        st.markdown('</div>', unsafe_allow_html=True)


# Tab 2: Role Fixer (Manual swapping & Auto-positioning)
with tab_roles:
    st.markdown("### Auto-Role Recognition & Fixer")
    st.write("The algorithm automatically assigns heroes to their meta positions. You can swap them manually if needed.")
    
    col_roles_rad, col_roles_dire = st.columns(2)
    
    with col_roles_rad:
        st.markdown('<div class="radiant-header">Radiant Roles</div>', unsafe_allow_html=True)
        if not rad_picks:
            st.info("Pick Radiant heroes first.")
        else:
            # Display dropdowns for each of the 5 positions
            # We filter positions to only show selected heroes count
            active_roles_rad = st.session_state['radiant_roles']
            
            for pos_idx in sorted(POSITIONS.keys()):
                # If team has fewer than pos_idx heroes, we don't render it
                if pos_idx > len(rad_picks):
                    continue
                
                # Find which hero is currently assigned to this position
                current_hero_id = None
                for h_id, p in active_roles_rad.items():
                    if p == pos_idx:
                        current_hero_id = h_id
                        break
                
                if current_hero_id is None:
                    # Fallback if somehow not mapped
                    current_hero_id = rad_picks[pos_idx - 1]
                    active_roles_rad[current_hero_id] = pos_idx
                    st.session_state['radiant_roles'] = active_roles_rad
                
                # Render dropdown to assign hero to this role
                # Options are the localized names of radiant picks
                options_names = [hero_id_to_name[h] for h in rad_picks]
                default_name = hero_id_to_name[current_hero_id]
                
                selected_name = st.selectbox(
                    f"{POSITIONS[pos_idx]}",
                    options=options_names,
                    index=options_names.index(default_name),
                    key=f"rad_pos_select_{pos_idx}"
                )
                
                selected_id = hero_name_to_id[selected_name]
                if selected_id != current_hero_id:
                    swap_roles('radiant_roles', pos_idx, selected_id)
                    st.rerun()
                    
                # Show innate ability badge for the hero in this role
                hero_obj = hero_id_to_obj[current_hero_id]
                if hero_obj['innate_name']:
                    st.markdown(f'<span class="innate-badge">Innate: {hero_obj["innate_name"]}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="innate-desc">{hero_obj["innate_desc"]}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

    with col_roles_dire:
        st.markdown('<div class="dire-header">Dire Roles</div>', unsafe_allow_html=True)
        if not dire_picks:
            st.info("Pick Dire heroes first.")
        else:
            active_roles_dire = st.session_state['dire_roles']
            
            for pos_idx in sorted(POSITIONS.keys()):
                if pos_idx > len(dire_picks):
                    continue
                
                current_hero_id = None
                for h_id, p in active_roles_dire.items():
                    if p == pos_idx:
                        current_hero_id = h_id
                        break
                
                if current_hero_id is None:
                    current_hero_id = dire_picks[pos_idx - 1]
                    active_roles_dire[current_hero_id] = pos_idx
                    st.session_state['dire_roles'] = active_roles_dire
                
                options_names = [hero_id_to_name[h] for h in dire_picks]
                default_name = hero_id_to_name[current_hero_id]
                
                selected_name = st.selectbox(
                    f"{POSITIONS[pos_idx]}",
                    options=options_names,
                    index=options_names.index(default_name),
                    key=f"dire_pos_select_{pos_idx}"
                )
                
                selected_id = hero_name_to_id[selected_name]
                if selected_id != current_hero_id:
                    swap_roles('dire_roles', pos_idx, selected_id)
                    st.rerun()
                    
                hero_obj = hero_id_to_obj[current_hero_id]
                if hero_obj['innate_name']:
                    st.markdown(f'<span class="innate-badge">Innate: {hero_obj["innate_name"]}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="innate-desc">{hero_obj["innate_desc"]}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)


# Tab 3: Laning Analysis
with tab_lanes:
    st.markdown("### Laning Stage Analysis (First 10 mins)")
    st.write("Predicted win rates for each lane based on historical gold/XP advantages at 10 minutes.")
    
    lanes_data = analysis['lanes']
    
    for lane_id in [1, 2, 3]:
        lane_name = "Lane 1 (Radiant Offlane vs Dire Safelane)" if lane_id == 1 else \
                    "Lane 2 (Midlane)" if lane_id == 2 else \
                    "Lane 3 (Radiant Safelane vs Dire Offlane)"
        
        st.markdown(f'<div class="lane-panel">', unsafe_allow_html=True)
        st.subheader(lane_name)
        
        # Display heroes in this lane
        l_data = lanes_data[lane_id]
        rad_lane_heroes = ", ".join([hero_id_to_name[h] for h in l_data['radiant_heroes']])
        dire_lane_heroes = ", ".join([hero_id_to_name[h] for h in l_data['dire_heroes']])
        
        st.write(f"🟢 **Radiant Heroes:** {rad_lane_heroes or 'None selected'}")
        st.write(f"🔴 **Dire Heroes:** {dire_lane_heroes or 'None selected'}")
        
        # Win rate indicator
        lane_rad_prob = l_data['radiant_win_prob']
        lane_dire_prob = 1.0 - lane_rad_prob
        
        st.markdown(f"""
        <div style="font-size:1.1rem; margin-top:5px;">
            Predicted Laning Outcome: 
            <span style="color:#39e3a6; font-weight:bold;">Radiant {lane_rad_prob*100:.1f}%</span> - 
            <span style="color:#ff4d6d; font-weight:bold;">{lane_dire_prob*100:.1f}% Dire</span>
        </div>
        """, unsafe_allow_html=True)
        st.progress(float(lane_rad_prob))
        st.markdown('</div>', unsafe_allow_html=True)


# Tab 4: Duos & Counters
with tab_details:
    st.markdown("### Duo Synergies & Counter-Pick Details")
    
    col_details_syn, col_details_m = st.columns(2)
    
    with col_details_syn:
        st.subheader("Duo Synergies (Same Team)")
        st.write("Highlights pairs that play significantly better together than their solo averages.")
        
        # Radiant
        st.markdown("**Radiant Duos:**")
        rad_synergies = [s for s in analysis['radiant_synergies'] if s['synergy'] > 0.015]
        if not rad_synergies:
            st.info("No strong Radiant synergies detected or draft is incomplete.")
        else:
            for s in rad_synergies:
                h1_name = hero_id_to_name[s['hero_id1']]
                h2_name = hero_id_to_name[s['hero_id2']]
                st.markdown(f"""
                <div class="synergy-panel">
                    🟢 <b>{h1_name}</b> + <b>{h2_name}</b>: <b>+{s['synergy']*100:.2f}%</b> win rate synergy
                </div>
                """, unsafe_allow_html=True)
                
        # Dire
        st.markdown("**Dire Duos:**")
        dire_synergies = [s for s in analysis['dire_synergies'] if s['synergy'] > 0.015]
        if not dire_synergies:
            st.info("No strong Dire synergies detected or draft is incomplete.")
        else:
            for s in dire_synergies:
                h1_name = hero_id_to_name[s['hero_id1']]
                h2_name = hero_id_to_name[s['hero_id2']]
                st.markdown(f"""
                <div class="synergy-panel">
                    🔴 <b>{h1_name}</b> + <b>{h2_name}</b>: <b>+{s['synergy']*100:.2f}%</b> win rate synergy
                </div>
                """, unsafe_allow_html=True)

    with col_details_m:
        st.subheader("Counter-Picks (Matchups)")
        st.write("Highlights direct matchups where a hero has a significant advantage against an opponent.")
        
        strong_counters = [m for m in analysis['matchups'] if abs(m['adv']) > 0.025]
        if not strong_counters:
            st.info("No strong counter matchups detected (requires heroes picked on both sides).")
        else:
            # Sort by absolute advantage descending
            strong_counters.sort(key=lambda x: abs(x['adv']), reverse=True)
            for m in strong_counters:
                rad_name = hero_id_to_name[m['rad_id']]
                dire_name = hero_id_to_name[m['dire_id']]
                adv_pct = m['adv'] * 100
                
                if adv_pct > 0:
                    st.markdown(f"""
                    <div class="matchup-panel">
                        🟢 <b>{rad_name}</b> counters 🔴 <b>{dire_name}</b> (<b>+{adv_pct:.2f}%</b> advantage)
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="matchup-panel">
                        🔴 <b>{dire_name}</b> counters 🟢 <b>{rad_name}</b> (<b>+{abs(adv_pct):.2f}%</b> advantage)
                    </div>
                    """, unsafe_allow_html=True)


# Tab 5: Smart Suggestions ("Suggest Best Pick")
with tab_suggestions:
    st.markdown("### Smart Hero Suggestions")
    st.write("If you have empty slots, select the team and position to get the top 5 optimized hero recommendations.")
    
    col_s_cfg1, col_s_cfg2 = st.columns(2)
    with col_s_cfg1:
        team_choice = st.radio("Suggest picks for:", options=["Radiant", "Dire"])
    with col_s_cfg2:
        role_choice = st.selectbox(
            "For Position / Role:",
            options=list(POSITIONS.keys()),
            format_func=lambda x: POSITIONS[x]
        )
        
    is_rad_team = (team_choice == "Radiant")
    team_picks = rad_picks if is_rad_team else dire_picks
    opp_picks = dire_picks if is_rad_team else rad_picks
    
    # Check if slot is empty or if we have room to pick
    if len(team_picks) >= 5:
        st.warning(f"The {team_choice} team already has 5 heroes. Remove a hero to get recommendations.")
    else:
        st.markdown(f"#### Top 5 recommendations for {team_choice} {POSITIONS[role_choice]}:")
        
        # Calculate suggestions
        suggestions = draft_analyzer.suggest_best_pick(
            team_picks, 
            opp_picks, 
            role_to_fill=role_choice, 
            is_radiant=is_rad_team
        )
        
        for idx, s in enumerate(suggestions):
            # Display recommendation cards
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #e9c46a;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.2rem; font-weight:bold; color:#e9c46a;">{idx+1}. {s['localized_name']}</span>
                    <span style="font-size:1.1rem; font-weight:bold; color:#39e3a6;">{s['win_prob']*100:.2f}% Win Probability</span>
                </div>
                <div style="font-size:0.9rem; color:#8d99ae; margin-top:3px;">
                    Base Hero Win Rate: <b>{s['base_win_rate']*100:.1f}%</b>
                </div>
                <div class="innate-badge">Innate: {s['innate_name'] or 'None'}</div>
            </div>
            """, unsafe_allow_html=True)
