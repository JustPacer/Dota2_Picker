import urllib.request
import urllib.parse
import json
import sqlite3
import time
import os

DB_PATH = 'opendota_cache.db'

def get_json(url):
    print(f"Fetching: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    raise Exception(f"Failed to fetch data from {url}")

def get_explorer_data(sql):
    url = 'https://api.opendota.com/api/explorer?sql=' + urllib.parse.quote_plus(sql)
    res = get_json(url)
    return res.get('rows', [])

def main():
    print("Starting OpenDota Cache Builder for Patch 7.41...")
    
    # 1. Fetch static data
    # Hero basic stats
    heroes_raw = get_json("https://api.opendota.com/api/heroes")
    # Hero stats (for win rate and other metadata)
    hero_stats_raw = get_json("https://api.opendota.com/api/heroStats")
    
    # Hero abilities lists
    hero_abilities = get_json("https://api.opendota.com/api/constants/hero_abilities")
    # Abilities details
    abilities_desc = get_json("https://api.opendota.com/api/constants/abilities")
    
    # Map heroStats by ID
    hero_stats_map = {h['id']: h for h in hero_stats_raw}
    
    # 2. Open SQLite Connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS heroes (
        id INTEGER PRIMARY KEY,
        name TEXT,
        localized_name TEXT,
        primary_attr TEXT,
        attack_type TEXT,
        roles TEXT,
        base_win_rate REAL,
        innate_name TEXT,
        innate_desc TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hero_lanes (
        hero_id INTEGER,
        lane INTEGER,
        total_games INTEGER,
        lane_wins INTEGER,
        PRIMARY KEY (hero_id, lane)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hero_matchups (
        hero_id INTEGER,
        opponent_id INTEGER,
        games_played INTEGER,
        wins INTEGER,
        PRIMARY KEY (hero_id, opponent_id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hero_synergies (
        hero_id1 INTEGER,
        hero_id2 INTEGER,
        games_played INTEGER,
        wins INTEGER,
        PRIMARY KEY (hero_id1, hero_id2)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hero_roles (
        hero_id INTEGER,
        role INTEGER,
        games_count INTEGER,
        PRIMARY KEY (hero_id, role)
    )""")
    
    # Commit table creation
    conn.commit()
    
    # 3. Process and Insert Heroes
    print("Processing hero metadata and innate abilities...")
    for h in heroes_raw:
        h_id = h['id']
        name = h['name']
        localized_name = h['localized_name']
        primary_attr = h['primary_attr']
        attack_type = h['attack_type']
        roles_str = ",".join(h['roles'])
        
        # Get base win rate (using pro_win / pro_pick or turbo_win / turbo_pick if available, 
        # but let's look at public winrate or simply calculate it from matches, or get from heroStats)
        h_stat = hero_stats_map.get(h_id, {})
        # Base winrate in professional matches or default pub win rate
        pro_win = h_stat.get('pro_win', 0)
        pro_pick = h_stat.get('pro_pick', 0)
        base_win_rate = pro_win / pro_pick if pro_pick > 0 else 0.50
        
        # Fallback to pub winrate (e.g. 5_win / 5_pick for Divine bracket or sum of all brackets)
        if base_win_rate == 0.50 or pro_pick < 50:
            # sum up pub picks and wins
            pub_picks = sum(h_stat.get(f"{rank}_pick", 0) for rank in ['1', '2', '3', '4', '5', '6', '7', '8'])
            pub_wins = sum(h_stat.get(f"{rank}_win", 0) for rank in ['1', '2', '3', '4', '5', '6', '7', '8'])
            if pub_picks > 0:
                base_win_rate = pub_wins / pub_picks
                
        # Resolve innate ability
        innate_name = None
        innate_desc = None
        
        # Abilities for this hero
        abils = hero_abilities.get(name, {}).get('abilities', [])
        for ab in abils:
            desc = abilities_desc.get(ab, {})
            if desc.get('is_innate', False):
                innate_name = desc.get('dname')
                innate_desc = desc.get('desc')
                break # Take the first innate ability found
                
        cursor.execute("""
        INSERT OR REPLACE INTO heroes (id, name, localized_name, primary_attr, attack_type, roles, base_win_rate, innate_name, innate_desc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (h_id, name, localized_name, primary_attr, attack_type, roles_str, base_win_rate, innate_name, innate_desc))
        
    conn.commit()
    print(f"Inserted {len(heroes_raw)} heroes into SQLite cache.")
    
    # 4. Fetch and cache Lane Stats
    print("Fetching laning win rates from OpenDota Explorer...")
    lane_sql = """
    WITH lane_stats AS (
      SELECT 
        pm.match_id,
        pm.lane,
        SUM(CASE WHEN pm.player_slot < 128 THEN pm.gold_t[11] ELSE 0 END) as gold_rad,
        SUM(CASE WHEN pm.player_slot < 128 THEN pm.xp_t[11] ELSE 0 END) as xp_rad,
        SUM(CASE WHEN pm.player_slot >= 128 THEN pm.gold_t[11] ELSE 0 END) as gold_dire,
        SUM(CASE WHEN pm.player_slot >= 128 THEN pm.xp_t[11] ELSE 0 END) as xp_dire
      FROM player_matches pm
      JOIN match_patch mp ON pm.match_id = mp.match_id
      WHERE mp.patch = '7.41'
        AND pm.gold_t IS NOT NULL 
        AND pm.gold_t[11] IS NOT NULL
        AND pm.xp_t IS NOT NULL
        AND pm.xp_t[11] IS NOT NULL
        AND pm.lane IN (1, 2, 3)
      GROUP BY pm.match_id, pm.lane
    ),
    player_lane_outcome AS (
      SELECT 
        pm.hero_id,
        pm.lane,
        CASE 
          WHEN pm.player_slot < 128 THEN (ls.gold_rad > ls.gold_dire AND ls.xp_rad > ls.xp_dire)
          ELSE (ls.gold_dire > ls.gold_rad AND ls.xp_dire > ls.xp_rad)
        END as lane_won
      FROM player_matches pm
      JOIN match_patch mp ON pm.match_id = mp.match_id
      JOIN lane_stats ls ON pm.match_id = ls.match_id AND pm.lane = ls.lane
      WHERE mp.patch = '7.41'
        AND pm.gold_t IS NOT NULL 
        AND pm.gold_t[11] IS NOT NULL
    )
    SELECT 
      hero_id,
      lane,
      COUNT(*) as total_lane_games,
      SUM(CASE WHEN lane_won THEN 1 ELSE 0 END) as lane_wins
    FROM player_lane_outcome
    GROUP BY hero_id, lane;
    """
    lane_rows = get_explorer_data(lane_sql)
    for r in lane_rows:
        cursor.execute("""
        INSERT OR REPLACE INTO hero_lanes (hero_id, lane, total_games, lane_wins)
        VALUES (?, ?, ?, ?)
        """, (r['hero_id'], r['lane'], r['total_lane_games'], r['lane_wins']))
    conn.commit()
    print(f"Cached {len(lane_rows)} lane stats entries.")
    time.sleep(1)
    
    # 5. Fetch and cache Matchups
    print("Fetching matchups from OpenDota Explorer...")
    matchup_sql = """
    SELECT 
      pm1.hero_id as hero_id,
      pm2.hero_id as opponent_id,
      COUNT(*) as games_played,
      SUM(CASE WHEN (pm1.player_slot < 128 AND m.radiant_win) OR (pm1.player_slot >= 128 AND NOT m.radiant_win) THEN 1 ELSE 0 END) as wins
    FROM player_matches pm1
    JOIN player_matches pm2 ON pm1.match_id = pm2.match_id
    JOIN matches m ON pm1.match_id = m.match_id
    JOIN match_patch mp ON pm1.match_id = mp.match_id
    WHERE mp.patch = '7.41'
      AND (pm1.player_slot < 128) != (pm2.player_slot < 128)
    GROUP BY pm1.hero_id, pm2.hero_id;
    """
    matchup_rows = get_explorer_data(matchup_sql)
    for r in matchup_rows:
        cursor.execute("""
        INSERT OR REPLACE INTO hero_matchups (hero_id, opponent_id, games_played, wins)
        VALUES (?, ?, ?, ?)
        """, (r['hero_id'], r['opponent_id'], r['games_played'], r['wins']))
    conn.commit()
    print(f"Cached {len(matchup_rows)} matchup entries.")
    time.sleep(1)
    
    # 6. Fetch and cache Synergies
    print("Fetching synergies from OpenDota Explorer...")
    synergy_sql = """
    SELECT 
      pm1.hero_id as hero_id1,
      pm2.hero_id as hero_id2,
      COUNT(*) as games_played,
      SUM(CASE WHEN (pm1.player_slot < 128 AND m.radiant_win) OR (pm1.player_slot >= 128 AND NOT m.radiant_win) THEN 1 ELSE 0 END) as wins
    FROM player_matches pm1
    JOIN player_matches pm2 ON pm1.match_id = pm2.match_id
    JOIN matches m ON pm1.match_id = m.match_id
    JOIN match_patch mp ON pm1.match_id = mp.match_id
    WHERE mp.patch = '7.41'
      AND (pm1.player_slot < 128) = (pm2.player_slot < 128)
      AND pm1.hero_id < pm2.hero_id
    GROUP BY pm1.hero_id, pm2.hero_id;
    """
    synergy_rows = get_explorer_data(synergy_sql)
    for r in synergy_rows:
        cursor.execute("""
        INSERT OR REPLACE INTO hero_synergies (hero_id1, hero_id2, games_played, wins)
        VALUES (?, ?, ?, ?)
        """, (r['hero_id1'], r['hero_id2'], r['games_played'], r['wins']))
    conn.commit()
    print(f"Cached {len(synergy_rows)} synergy entries.")
    time.sleep(1)
    
    # 7. Fetch and cache Role Frequencies
    print("Fetching role frequencies from OpenDota Explorer...")
    role_sql = """
    WITH player_gpm_rank AS (
      SELECT 
        pm.match_id,
        pm.hero_id,
        pm.player_slot,
        pm.lane_role,
        pm.gold_per_min,
        ROW_NUMBER() OVER(PARTITION BY pm.match_id, (pm.player_slot >= 128) ORDER BY pm.gold_per_min DESC) as team_gpm_rank
      FROM player_matches pm
      JOIN match_patch mp ON pm.match_id = mp.match_id
      WHERE mp.patch = '7.41'
    ),
    assigned_roles AS (
      SELECT 
        hero_id,
        CASE 
          WHEN lane_role = 2 THEN 2
          WHEN lane_role = 1 AND team_gpm_rank <= 2 THEN 1
          WHEN lane_role = 3 AND team_gpm_rank <= 3 THEN 3
          WHEN lane_role = 1 AND team_gpm_rank > 2 THEN 5
          WHEN lane_role = 3 AND team_gpm_rank > 3 THEN 4
          ELSE 
            CASE 
              WHEN team_gpm_rank = 1 THEN 1
              WHEN team_gpm_rank = 2 THEN 2
              WHEN team_gpm_rank = 3 THEN 3
              WHEN team_gpm_rank = 4 THEN 4
              ELSE 5
            END
        END as assigned_pos
      FROM player_gpm_rank
    )
    SELECT 
      hero_id,
      assigned_pos as role,
      COUNT(*) as games_count
    FROM assigned_roles
    GROUP BY hero_id, assigned_pos;
    """
    role_rows = get_explorer_data(role_sql)
    for r in role_rows:
        cursor.execute("""
        INSERT OR REPLACE INTO hero_roles (hero_id, role, games_count)
        VALUES (?, ?, ?)
        """, (r['hero_id'], r['role'], r['games_count']))
    conn.commit()
    print(f"Cached {len(role_rows)} role frequency entries.")
    
    # Close connection
    conn.close()
    print("Database caching complete! local cache is saved in", DB_PATH)

if __name__ == "__main__":
    main()
