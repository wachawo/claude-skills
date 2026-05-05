# When to mock

Mock only at **system boundaries**:

- External APIs (payments, email, etc.)
- Databases (sometimes — a test database is often better)
- Time/randomness
- The file system (sometimes)

Do not mock:

- Your own classes/modules
- Internal collaborators
- Anything under your control

## Designing for mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in from the outside instead of creating them inside:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-like interfaces over generic fetchers**

Create separate functions for each external operation instead of one generic function with conditional logic:

```typescript
// GOOD: Each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: Mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK-style approach means:
- Each mock returns one specific shape
- No conditional logic in the test setup
- Easier to see which endpoints a test exercises
- Per-endpoint type safety
