---
name: express-rest-http
description: Maps Express endpoints to REST-ish resources with POST action verbs for mutations, mandatory security middleware, canonical status codes, OpenAPI documentation, pagination limit and offset, partial field queries, native fetch for outbound HTTP. Do not use when replacing Express with another server framework.
---

# Express, REST-style HTTP APIs

## Procedures

**When designing controllers, routers, or HTTP clients alongside Express**

1. Map HTTP handling exclusively through Express; do not substitute alternative routers or frameworks unless the repository explicitly deprecates Express.
2. Model collection resources using plural English nouns nested only where relationships require navigation (`/playlists/:playlistId/videos`).
3. Keep composite resource segments kebab-case (`scheduled-events`, `process-payment`).
4. Prevent routes deeper than roughly three navigable segments; reshape paths when chains become unwieldy, unless security partitioning demands explicit namespaces such as `/public` or scoped user routes (`/users/:userId`).
5. Represent deliberate mutations via `POST` with verb-like action segments instead of cramming verbs into rigid `PUT /resource/:id` patterns when business flows demand clarity (`POST /users/:userId/change-password`).
6. Transmit JSON payloads for request and response bodies unless a contract mandates another representation.
7. Apply authentication and authorization middleware to every surfaced route cluster; replicate existing security topology before diverging paths.
8. Return `200` for successful reads and commands when no alternative success code applies, `404` when entities are absent, `500` only for genuinely unexpected faults, `422` for business-rule violations surfaced to callers, `400` for malformed input, `401` when unauthenticated, `403` when authenticated but forbidden.
9. Maintain OpenAPI documentation enumerating verbs, payloads, headers, and response codes alongside handler implementations.
10. Add `limit` and `offset` query parameters for heavyweight list endpoints.
11. Support partial-response selection through query hints such as `fields=id,name,createdAt` when listing large aggregates.
12. Reach external HTTP services with native `fetch` (`async` / `await`, validate `response.ok`, parse structured bodies consciously) instead of layering convenience HTTP clients purely for ergonomics.

## Error Handling

1. When ambiguity arises between REST purity and pragmatic action routes, prioritize documented POST verbs and OpenAPI narratives over silent divergences.
2. When outbound `fetch` calls fail intermittently, standardize retries and error translation at integration boundaries before controllers leak raw transport errors.
