const stripe = Stripe("pk_test_51PuvJrG4K28d83uR0Lez916OzIWEb15JzgDX9JdbMJ9qtzQb3BUw3OEqRFwuSm54oVVvEKhM9y3yhUWCX73jkvDd00PcQ12Whk");
const elements = stripe.elements();

const cardElement = elements.create('card');
cardElement.mount('#card-element');

const form = document.getElementById('payment-form');
const errorMessage = document.getElementById('error-message');

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const { token, error } = await stripe.createToken(cardElement);

  if (error) {
    errorMessage.textContent = error.message;
  } else {
    // Send the token to your server
    const response = await fetch('/charge', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ tokenId: token.id })
    });

    const result = await response.json();

    if (result.error) {
      errorMessage.textContent = result.error;
    } else {
      // Payment successful
      window.location.href = '/success.html';
    }
  }
});
