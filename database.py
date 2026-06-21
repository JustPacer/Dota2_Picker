import sqlite3
import os

DB_PATH = 'opendota_cache.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_heroes():
    """
    Returns list of all heroes with basic information, sorted by localized_name.
    """
    if not os.path.exists(DB_PATH):
        return []
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, localized_name, primary_attr, attack_type, roles, base_win_rate, innate_name, innate_desc 
            FROM heroes 
            ORDER BY localized_name ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_lane_stats(hero_id):
    """
    Returns a dictionary of lane (1, 2, 3) -> (total_games, lane_wins) for a hero.
    """
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT lane, total_games, lane_wins FROM hero_lanes WHERE hero_id = ?", (hero_id,))
        rows = cursor.fetchall()
        return {row['lane']: (row['total_games'], row['lane_wins']) for row in rows}
    finally:
        conn.close()

def get_matchups_for_hero(hero_id):
    """
    Returns a dictionary of opponent_id -> (games_played, wins) for a hero.
    Here, wins is the number of times hero_id beat opponent_id.
    """
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT opponent_id, games_played, wins FROM hero_matchups WHERE hero_id = ?", (hero_id,))
        rows = cursor.fetchall()
        return {row['opponent_id']: (row['games_played'], row['wins']) for row in rows}
    finally:
        conn.close()

def get_synergies_for_hero(hero_id):
    """
    Returns a dictionary of partner_id -> (games_played, wins) for a hero.
    Handles same-team pairs (hero_id1, hero_id2) in both orders since hero_id1 < hero_id2 in DB.
    """
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Find where hero_id is hero_id1
        cursor.execute("SELECT hero_id2 as partner_id, games_played, wins FROM hero_synergies WHERE hero_id1 = ?", (hero_id,))
        rows1 = cursor.fetchall()
        
        # Find where hero_id is hero_id2
        cursor.execute("SELECT hero_id1 as partner_id, games_played, wins FROM hero_synergies WHERE hero_id2 = ?", (hero_id,))
        rows2 = cursor.fetchall()
        
        synergies = {}
        for row in rows1:
            synergies[row['partner_id']] = (row['games_played'], row['wins'])
        for row in rows2:
            synergies[row['partner_id']] = (row['games_played'], row['wins'])
            
        return synergies
    finally:
        conn.close()

def get_role_weights(hero_id):
    """
    Returns a dictionary of role (1..5) -> games_count for a hero.
    """
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT role, games_count FROM hero_roles WHERE hero_id = ?", (hero_id,))
        rows = cursor.fetchall()
        return {row['role']: row['games_count'] for row in rows}
    finally:
        conn.close()
