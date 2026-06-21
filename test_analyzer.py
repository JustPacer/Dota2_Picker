import database
import draft_analyzer

def test_database():
    print("Testing database module...")
    heroes = database.get_all_heroes()
    assert len(heroes) > 0, "No heroes fetched from DB!"
    print(f"  Successfully fetched {len(heroes)} heroes.")
    
    # Check some test heroes for innate abilities
    ax = [h for h in heroes if h['localized_name'] == 'Axe']
    assert len(ax) == 1, "Axe not found!"
    ax_hero = ax[0]
    print(f"  Axe innate: {ax_hero['innate_name']} - {ax_hero['innate_desc'][:60]}...")
    assert ax_hero['innate_name'] == 'One Man Army', "Axe innate ability mismatch!"
    
    am = [h for h in heroes if h['localized_name'] == 'Anti-Mage']
    assert len(am) == 1, "Anti-Mage not found!"
    am_hero = am[0]
    print(f"  Anti-Mage innate: {am_hero['innate_name']} - {am_hero['innate_desc'][:60]}...")
    assert am_hero['innate_name'] == 'Persecutor', "Anti-Mage innate ability mismatch!"

def test_role_fixer():
    print("\nTesting role fixer (auto-recognition)...")
    # Axe, Anti-Mage, Crystal Maiden, Storm Spirit, Rubick
    heroes = database.get_all_heroes()
    hero_map = {h['localized_name']: h['id'] for h in heroes}
    
    test_team = [
        hero_map['Anti-Mage'],
        hero_map['Axe'],
        hero_map['Crystal Maiden'],
        hero_map['Storm Spirit'],
        hero_map['Rubick']
    ]
    
    roles = draft_analyzer.assign_roles_partial(test_team)
    print("  Assigned roles:")
    for h_id, pos in roles.items():
        h_name = next(h['localized_name'] for h in heroes if h['id'] == h_id)
        print(f"    {h_name}: Position {pos}")
        
    assert roles[hero_map['Anti-Mage']] == 1, "Anti-Mage should be Pos 1"
    assert roles[hero_map['Storm Spirit']] == 2, "Storm Spirit should be Pos 2"
    assert roles[hero_map['Axe']] == 3, "Axe should be Pos 3"
    assert roles[hero_map['Rubick']] == 4, "Rubick should be Pos 4"
    assert roles[hero_map['Crystal Maiden']] == 5, "Crystal Maiden should be Pos 5"
    print("  Role assignment tests passed!")

def test_analysis():
    print("\nTesting draft analysis...")
    heroes = database.get_all_heroes()
    hero_map = {h['localized_name']: h['id'] for h in heroes}
    
    radiant = [
        hero_map['Anti-Mage'],
        hero_map['Axe'],
        hero_map['Crystal Maiden'],
        hero_map['Storm Spirit'],
        hero_map['Rubick']
    ]
    
    dire = [
        hero_map['Lifestealer'],
        hero_map['Slardar'],
        hero_map['Lina'],
        hero_map['Lion'],
        hero_map['Abaddon']
    ]
    
    result = draft_analyzer.analyze_draft(radiant, dire)
    print(f"  Radiant Win Probability: {result['radiant_win_prob']*100:.2f}%")
    print(f"  Radiant Base WR: {result['radiant_base_wr']*100:.2f}%")
    print(f"  Dire Base WR: {result['dire_base_wr']*100:.2f}%")
    print("  Lane Win Probabilities:")
    print(f"    Lane 1 (Radiant Offlane vs Dire Safelane): {result['lanes'][1]['radiant_win_prob']*100:.2f}%")
    print(f"    Lane 2 (Midlane): {result['lanes'][2]['radiant_win_prob']*100:.2f}%")
    print(f"    Lane 3 (Radiant Safelane vs Dire Offlane): {result['lanes'][3]['radiant_win_prob']*100:.2f}%")
    
    # Check matchups
    print(f"  Number of matchups processed: {len(result['matchups'])}")
    assert len(result['matchups']) == 25
    
    # Check synergies
    print(f"  Number of Radiant synergies: {len(result['radiant_synergies'])}")
    assert len(result['radiant_synergies']) == 10

def test_suggestions():
    print("\nTesting suggest best pick...")
    heroes = database.get_all_heroes()
    hero_map = {h['localized_name']: h['id'] for h in heroes}
    
    # Partial Radiant draft (needs Pos 1 carry)
    radiant = [
        hero_map['Axe'],
        hero_map['Crystal Maiden'],
        hero_map['Storm Spirit'],
        hero_map['Rubick']
    ]
    
    dire = [
        hero_map['Lifestealer'],
        hero_map['Slardar'],
        hero_map['Lina'],
        hero_map['Lion'],
        hero_map['Abaddon']
    ]
    
    suggestions = draft_analyzer.suggest_best_pick(radiant, dire, role_to_fill=1, is_radiant=True)
    print("  Top 5 suggestions for Radiant Carry (Pos 1):")
    for idx, s in enumerate(suggestions):
        print(f"    {idx+1}. {s['localized_name']} (Win probability if picked: {s['win_prob']*100:.2f}%)")
    assert len(suggestions) == 5

if __name__ == "__main__":
    test_database()
    test_role_fixer()
    test_analysis()
    test_suggestions()
    print("\nAll tests completed successfully!")
