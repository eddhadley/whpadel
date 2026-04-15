# West Hants Padel Matchmaker - Test Report

**Date:** 2026-04-15 12:11:07  
**Total Tests:** 111  
**Passed:** 111 ✅  
**Failed:** 0 ❌  
**Pass Rate:** 100.0%  

---

## Authentication (11/11)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Login page loads | ✅ Pass |  |
| 2 | Login with valid credentials | ✅ Pass |  |
| 3 | Top bar shows user name | ✅ Pass | 
            
                
                    🏸 West Ha |
| 4 | Logout returns to login page | ✅ Pass |  |
| 5 | Wrong password shows error | ✅ Pass |  |
| 6 | Register tab switches form | ✅ Pass |  |
| 7 | Registration leads to verify page | ✅ Pass |  |
| 8 | Resend code button visible | ✅ Pass |  |
| 9 | Sign out link on verify page | ✅ Pass |  |
| 10 | Forgot password form opens | ✅ Pass |  |
| 11 | Back to login from forgot password | ✅ Pass |  |

## Games List (8/8)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Games page shows game cards | ✅ Pass | 2 cards |
| 2 | Section header shows game count | ✅ Pass | Available Games
                    2 games availa |
| 3 | Skill filter chips visible | ✅ Pass |  |
| 4 | All filter chips present (8 total) | ✅ Pass | 8 chips |
| 5 | Skill filter click activates chip | ✅ Pass |  |
| 6 | Game card shows court name | ✅ Pass |  |
| 7 | Game card shows level badges | ✅ Pass |  |
| 8 | Game card shows player avatars | ✅ Pass |  |

## Game Detail Modal (6/6)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Game detail modal opens | ✅ Pass |  |
| 2 | Modal shows court info | ✅ Pass |  |
| 3 | Modal shows players section | ✅ Pass |  |
| 4 | Share/copy link button visible | ✅ Pass |  |
| 5 | Close button visible | ✅ Pass |  |
| 6 | Modal closes on button click | ✅ Pass |  |

## My Games (3/3)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | My Games page loads | ✅ Pass |  |
| 2 | My Games shows user's games | ✅ Pass | 1 games |
| 3 | Shows 'Hosting' badge for created game | ✅ Pass |  |

## Courts Availability (9/9)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Courts page loads | ✅ Pass |  |
| 2 | Date picker visible | ✅ Pass |  |
| 3 | Court grid renders | ✅ Pass |  |
| 4 | Grid shows Court 1 | ✅ Pass |  |
| 5 | Grid shows Court 2 | ✅ Pass |  |
| 6 | Grid shows Court 3 | ✅ Pass |  |
| 7 | Available time slots shown | ✅ Pass | 34 slots |
| 8 | Booked slots shown for seeded games | ✅ Pass | 2 booked |
| 9 | Clicking available slot opens create form | ✅ Pass |  |

## Create Game (12/12)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | FAB create button visible | ✅ Pass |  |
| 2 | FAB opens create game form | ✅ Pass |  |
| 3 | Elite-Live warning shown | ✅ Pass |  |
| 4 | 3 court options shown | ✅ Pass | 3 courts |
| 5 | Court selection works | ✅ Pass |  |
| 6 | Date input present | ✅ Pass |  |
| 7 | Time slots displayed | ✅ Pass | 8 available |
| 8 | Time slot selection works | ✅ Pass |  |
| 9 | Level range pills shown (7) | ✅ Pass | 7 pills |
| 10 | Reserved slots dropdown present | ✅ Pass |  |
| 11 | Notes field present | ✅ Pass |  |
| 12 | Game created successfully (redirected to list) | ✅ Pass |  |

## Join & Leave Game (6/6)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Login as second user (Bob) | ✅ Pass |  |
| 2 | Quick join buttons visible | ✅ Pass | 2 joinable |
| 3 | Quick join click processes | ✅ Pass |  |
| 4 | Modal shows Bob as player after join | ✅ Pass |  |
| 5 | Leave game button works | ✅ Pass |  |
| 6 | Join game via modal works | ✅ Pass |  |

## Profile Page (19/19)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Profile shows user name | ✅ Pass |  |
| 2 | Profile shows username | ✅ Pass |  |
| 3 | Profile shows email | ✅ Pass |  |
| 4 | Profile avatar visible | ✅ Pass |  |
| 5 | Edit name inputs visible | ✅ Pass |  |
| 6 | Save name enabled after change | ✅ Pass |  |
| 7 | Name save works | ✅ Pass | status_visible=False, name=Bobby |
| 8 | Current password field present | ✅ Pass |  |
| 9 | New password field present | ✅ Pass |  |
| 10 | Confirm password field present | ✅ Pass |  |
| 11 | Change password button initially disabled | ✅ Pass |  |
| 12 | Change password button enables when filled | ✅ Pass |  |
| 13 | Password change shows status | ✅ Pass |  |
| 14 | 3 notification checkboxes present | ✅ Pass | 3 found |
| 15 | Notification toggle works | ✅ Pass |  |
| 16 | 7 skill level options in profile | ✅ Pass | 7 options |
| 17 | Colour grading guide visible | ✅ Pass |  |
| 18 | Version info shown | ✅ Pass |  |
| 19 | Sign out button visible | ✅ Pass |  |

## Navigation (6/6)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Bottom nav has 4 tabs | ✅ Pass | 4 tabs |
| 2 | Games nav tab works | ✅ Pass |  |
| 3 | My Games nav tab works | ✅ Pass |  |
| 4 | Courts nav tab works | ✅ Pass |  |
| 5 | Profile nav tab works | ✅ Pass |  |
| 6 | Active nav tab highlighted | ✅ Pass |  |

## Host Game Management (UI) (4/4)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Remove player buttons visible for host | ✅ Pass |  |
| 2 | Remove player via UI succeeds | ✅ Pass |  |
| 3 | Player count decreased after removal | ✅ Pass |  |
| 4 | Non-host does not see remove buttons | ✅ Pass |  |

## Cancel Game (Creator) (2/2)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Cancel game button visible for creator | ✅ Pass |  |
| 2 | Cancel game processes | ✅ Pass |  |

## Host Game Management (API) (9/9)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Non-host cannot remove player | ✅ Pass |  |
| 2 | Host can remove player | ✅ Pass |  |
| 3 | Removed player no longer in game | ✅ Pass |  |
| 4 | Host cannot remove self | ✅ Pass |  |
| 5 | Host can update reserved slots | ✅ Pass |  |
| 6 | Reserved slots updated to 2 | ✅ Pass |  |
| 7 | Non-host cannot update reserved slots | ✅ Pass |  |
| 8 | Reserved slots rejects over-capacity | ✅ Pass |  |
| 9 | Reserved slots rejects negative value | ✅ Pass |  |

## API Endpoints (16/16)

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | GET /api/health returns 200 | ✅ Pass |  |
| 2 | GET /api/skill-levels returns data | ✅ Pass |  |
| 3 | GET /api/courts returns 3 courts | ✅ Pass |  |
| 4 | GET /api/time-slots returns slots | ✅ Pass |  |
| 5 | POST /api/login returns token | ✅ Pass |  |
| 6 | GET /api/me returns user | ✅ Pass |  |
| 7 | GET /api/games returns list | ✅ Pass |  |
| 8 | GET /api/courts/availability returns grid | ✅ Pass |  |
| 9 | GET /api/me without token returns 401 | ✅ Pass |  |
| 10 | POST /api/games creates game | ✅ Pass |  |
| 11 | GET /api/games/<id> returns game | ✅ Pass |  |
| 12 | POST /api/games/<id>/join works | ✅ Pass |  |
| 13 | POST /api/games/<id>/leave works | ✅ Pass |  |
| 14 | POST /api/me/name updates name | ✅ Pass |  |
| 15 | POST /api/me/notifications works | ✅ Pass |  |
| 16 | Duplicate join returns error | ✅ Pass |  |
