"""The user's own x402 payer on Base mainnet (USDC, scheme exact)."""

from __future__ import annotations

from collections.abc import Callable

from eth_account import Account
from eth_account.signers.local import LocalAccount
from x402 import SchemeRegistration, x402Client, x402ClientConfig
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.schemas.hooks import PaymentCreatedContext

from .budget import atomic_to_usd

BASE_MAINNET = "eip155:8453"
# The only payee this client pays: the facts402 services' receiving address. A server (or anything spoofing
# one) cannot redirect a payment elsewhere; the spend caps bound everything else.
FACTS402_PAY_TO = "0x5498b0Aa90cd56F8962CBd136DF3D3769C85f149"


def facts402_only(version: int, requirements: list) -> list:
    """x402 policy: pay facts402 only, and only with a gasless EIP-3009 authorization (no Permit2 approvals)."""
    return [
        r for r in requirements
        if r.pay_to.lower() == FACTS402_PAY_TO.lower() and (r.extra or {}).get("assetTransferMethod") != "permit2"
    ]


class Wallet:
    def __init__(self, account: LocalAccount) -> None:
        self._account = account

    @classmethod
    def from_key(cls, private_key: str) -> Wallet:
        try:
            return cls(Account.from_key(private_key))
        except Exception:  # eth_account raises several types; never echo the key
            raise ValueError("X402_PRIVATE_KEY is set but is not a valid hex private key") from None

    @property
    def address(self) -> str:
        return self._account.address

    def __repr__(self) -> str:
        return f"Wallet({self.address})"

    def x402_client(self, cap_atomic: int, on_signed: Callable[[int], None]) -> x402Client:
        """A client that signs at most `cap_atomic` USDC to facts402 on Base and reports what it signed."""
        client = x402Client.from_config(
            x402ClientConfig(
                schemes=[SchemeRegistration(network=BASE_MAINNET, client=ExactEvmScheme(signer=EthAccountSigner(self._account)))],
                policies=[facts402_only],
                spend_controls={"max_amount_per_payment": f"${atomic_to_usd(cap_atomic)}"},
            )
        )

        def record(ctx: PaymentCreatedContext) -> None:
            on_signed(int(ctx.selected_requirements.amount))

        return client.on_after_payment_creation(record)
