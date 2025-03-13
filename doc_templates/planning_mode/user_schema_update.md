# User Node Schema Update

## Overview
This document describes the updated User node schema in Neo4j to support OAuth authentication.

## User Node

### Properties
- **id**: String (UUID)
  - **Description**: Unique identifier for the user
  - **Constraints**: Required, Unique
  - **Example**: "550e8400-e29b-41d4-a716-446655440000"

- **email**: String
  - **Description**: User's email address, used for authentication
  - **Constraints**: Required, Unique
  - **Validation**: Valid email format
  - **Example**: "user@example.com"

- **name**: String
  - **Description**: User's display name
  - **Constraints**: Required
  - **Validation**: 2-100 characters
  - **Example**: "John Doe"

- **password**: String
  - **Description**: Hashed password (only for local authentication)
  - **Constraints**: Optional (required for local auth, not for OAuth)
  - **Example**: "$2b$12$HKveMsPlst15reZfKleV.Oi8VhPgNxPwpbDty.MnKgsVuCIUu8GDu"

- **image**: String
  - **Description**: URL to user's avatar image
  - **Constraints**: Optional
  - **Validation**: Valid URL format
  - **Example**: "https://example.com/avatars/johndoe.png"

- **provider**: String
  - **Description**: Authentication provider (e.g., "google", "local")
  - **Constraints**: Required
  - **Example**: "google"

- **provider_user_id**: String
  - **Description**: User ID from the provider
  - **Constraints**: Required for OAuth users
  - **Example**: "123456789"

- **email_verified**: Boolean
  - **Description**: Whether the email has been verified by the provider
  - **Constraints**: Optional
  - **Example**: true

- **locale**: String
  - **Description**: User's locale preference from the provider
  - **Constraints**: Optional
  - **Example**: "en"

- **created_at**: DateTime
  - **Description**: When the user account was created
  - **Constraints**: Required, Auto-generated
  - **Example**: "2025-01-01T12:00:00Z"

- **updated_at**: DateTime
  - **Description**: When the user account was last updated
  - **Constraints**: Required, Auto-updated
  - **Example**: "2025-03-15T09:30:00Z"

### Constraints
```cypher
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE

CREATE CONSTRAINT user_email_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.email IS UNIQUE
```

### Indexes
```cypher
CREATE INDEX user_provider_idx IF NOT EXISTS
FOR (u:User) ON (u.provider)

CREATE INDEX user_provider_user_id_idx IF NOT EXISTS
FOR (u:User) ON (u.provider, u.provider_user_id)
```

## Example Data

### Local Authentication User
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "password": "$2b$12$HKveMsPlst15reZfKleV.Oi8VhPgNxPwpbDty.MnKgsVuCIUu8GDu",
  "image": "https://example.com/avatars/johndoe.png",
  "provider": "local",
  "provider_user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email_verified": false,
  "locale": "en",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z"
}
```

### OAuth Authentication User
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "email": "oauth.user@gmail.com",
  "name": "OAuth User",
  "image": "https://lh3.googleusercontent.com/a/profile-image",
  "provider": "google",
  "provider_user_id": "123456789",
  "email_verified": true,
  "locale": "en-US",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z"
}
```

## Common Queries

### Find User by Provider and Provider User ID
```cypher
MATCH (u:User {provider: $provider, provider_user_id: $provider_user_id})
RETURN u
```

### Find User by Email
```cypher
MATCH (u:User {email: $email})
RETURN u
```

### Update OAuth User Information
```cypher
MATCH (u:User {id: $id})
SET u.name = $name,
    u.image = $image,
    u.provider = $provider,
    u.provider_user_id = $provider_user_id,
    u.email_verified = $email_verified,
    u.locale = $locale,
    u.updated_at = datetime($updated_at)
RETURN u