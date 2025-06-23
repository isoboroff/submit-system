# Issues

This file is for issues to solve on the login_gov migration

- [x] #1 Add new login page
- [x] #2 Add handshake sequence to views.py
- [x] #3 Link in authentication()
- [x] #4 Complete auth_login()
- [x] #5 Authenticate users by email and not username
- [ ] #6 Update new user creation process
- [ ] #7 Login needs to route a new user to the user creation process
- [ ] #8 Add unique_id to UserProfile

## Issue detail

### 1. Add new login page
This needs a login page that only has a button to go to login.gov.
It should also have FAQ text to explain the change.

### 2. Add handshake sequence to views.py **IN PROGRESS**
Port login sequence from bench2/back-end/server.py.
This is almost complete but for hooking into authenticate() and auth_login()
To do that, we need [#5](#5-authenticate-users-by-email-and-not-username) identify users by their email address and not by username.

### 3. Link in authentication()
Done

### 4. Complete auth_login()
Done

### 5. Authenticate users by email and not username
This is tricky because we need to have email addresses be unique.  Fortunately we handle this in user creation when we clean the email field (forms.SignupForm).
We have to revise the signup sequence.
The next step is to add an authentication backend.
Done

### 6. Update new user creation process

### 7. Login needs to route a new user to the user creation process

### 8. Add unique_id to the UserProfile
This ID comes from login.gov as the 'sub' parameter and identifies the login.gov user.
We are going to store that with the profile, and (if we have it) check that it matches at login.
If it doesn't match, we have a different login user.  That might be because a user deleted and recreated
their login.gov profile.