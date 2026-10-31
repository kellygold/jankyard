"""Historical leaderboard progress remains readable after transport retirement."""
from app.models.leaderboard import LeaderboardEntry


def test_progress_is_not_limited_to_top_thousand(client,db,test_user,auth_headers):
    db.add_all([LeaderboardEntry(username=f'other_{i}',challenge_name='heist',difficulty='easy',best_score=100,best_steps=1) for i in range(1001)])
    db.add(LeaderboardEntry(username=test_user.username,user_id=test_user.id,challenge_name='heist',difficulty='easy',best_score=1,best_steps=3))
    db.commit()
    assert client.get('/leaderboard/heist/progress',headers=auth_headers).json()['unlocked_levels'] == [1,2]
