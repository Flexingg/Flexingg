# Social App Documentation

## Overview
The `social` app provides all the social features for the Flexingg application. This includes friendships, groups, and leaderboards.

## Models

### `Friendship`
- **Description**: Represents a friendship between two users.
- **Fields**:
  - `from_user`, `to_user`: `ForeignKey` to the `UserProfile` model.
  - `status`: The status of the friendship (`pending`, `accepted`, `declined`).

### `Group`
- **Description**: Represents a group of users.
- **Fields**:
  - `name`: The name of the group.
  - `description`: A description of the group.
  - `creator`: A `ForeignKey` to the `UserProfile` who created the group.
  - `members`: A `ManyToManyField` to `UserProfile` through the `GroupMembership` model.

### `GroupMembership`
- **Description**: A through model for the `Group.members` relationship, which stores additional information about a user's membership in a group.
- **Fields**:
  - `user`: A `ForeignKey` to `UserProfile`.
  - `group`: A `ForeignKey` to `Group`.
  - `role`: The user's role in the group (`admin` or `member`).

## Views

### Friendship Views
- `send_friend_request`: Creates a new `Friendship` object with a status of `pending`.
- `accept_friend_request`: Changes the status of a `Friendship` to `accepted`.
- `decline_friend_request`: Deletes a `Friendship` object.
- `remove_friend`: Deletes a `Friendship` object.
- `friend_list`: Displays a list of the user's friends.
- `friend_requests`: Displays a list of incoming friend requests.
- `search_users`: Searches for users to send friend requests to.

### Group Views
- `group_list`: Displays a list of all groups.
- `group_detail`: Displays the details of a specific group, including its members.
- `create_group`: Handles the creation of a new group.
- `join_group`: Adds the current user to a group.
- `leave_group`: Removes the current user from a group.

### `social_main`
- **Purpose**: The main view for the social section, which displays leaderboards.
- **Functionality**:
  - It can filter the leaderboard by category (e.g., 'steps', 'lifts', 'calories'), history ('All Time', 'Weekly', 'Monthly'), and scope ('Global', 'Friends', 'Group').
  - It calculates the metric for each user based on the selected filters and displays the top users.

## URLs
The `social` app has URLs for all of the friendship and group views, as well as the main `social_main` view.
