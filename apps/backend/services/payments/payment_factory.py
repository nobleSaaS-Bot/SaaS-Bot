from models.payment import PaymentProvider
from services.payments.stripe_provider import StripeProvider
from services.payments.telebirr_provider import TelebirrProvider
from services.payments.mpesa_provider import MpesaProvider


def get_payment_provider(provider: PaymentProvider):
    if provider == PaymentProvider.stripe:
        return StripeProvider()
    elif provider == PaymentProvider.telebirr:
        return TelebirrProvider()
    elif provider == PaymentProvider.mpesa:
        return MpesaProvider()
    else:
        raise ValueError(f"Unsupported payment provider: {provider}")
