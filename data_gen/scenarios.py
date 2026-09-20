"""
Scenario content bank for synthetic Voice-of-Customer call transcripts.

Everything here is fictional. The bank name, agents, customers, account
numbers and dollar amounts are all synthetic and generated for demo
purposes only -- none of it represents real people, accounts or events.
"""

import random

BANK_NAME = "Meridian Bank"
APP_NAME = "Meridian Mobile"

FIRST_NAMES = [
    "Jordan", "Casey", "Morgan", "Riley", "Taylor", "Avery", "Reese", "Quinn",
    "Hayden", "Rowan", "Sydney", "Emerson", "Dakota", "Skyler", "Peyton",
    "Elliot", "Marley", "Kendall", "Shawn", "Devon", "Alexis", "Cameron",
]
LAST_NAMES = [
    "Blake", "Reyes", "Ellis", "Nakamura", "Osei", "Carrington", "Vasquez",
    "Whitfield", "Okafor", "Lindqvist", "Bergstrom", "Marsh", "Delgado",
    "Winslow", "Abara", "Fontaine", "Kowalski", "Nazari", "Prescott", "Diallo",
]

LOBS = {}


def _rand_name(rng=random):
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _rand_amount(lo, hi, rng=random):
    return round(rng.uniform(lo, hi), 2)


def register(lob_name, code, complaints, opportunities, neutral):
    LOBS[lob_name] = {
        "code": code,
        "complaints": complaints,
        "opportunities": opportunities,
        "neutral": neutral,
    }


# ---------------------------------------------------------------------------
# Retail & Consumer Banking
# ---------------------------------------------------------------------------
register(
    "Retail & Consumer Banking",
    "RETAIL",
    complaints=[
        {
            "category": "Overdraft fees",
            "open": "i got charged an overdraft fee of {fee} and i dont understand why because i thought i had money in there",
            "detail": "this is the {count} time this year and nobody explained the fee to me when i opened the account",
        },
        {
            "category": "Mobile app outage",
            "open": "the {app} has been down since {date_ref} and i cant check my balance or pay anything",
            "detail": "i tried logging in like five times and it just keeps spinning and then it logs me out",
        },
        {
            "category": "Branch wait times",
            "open": "i waited {wait} minutes in line at the branch on {date_ref} just to deposit a check",
            "detail": "there were only two tellers working on a friday afternoon which is ridiculous",
        },
        {
            "category": "Account fees / disclosure",
            "open": "nobody told me this checking account had a monthly maintenance fee of {fee}",
            "detail": "i want that fee refunded because i was never notified when i signed up",
        },
        {
            "category": "Debit card issue",
            "open": "my debit card keeps getting declined and i have plenty of money in the account ending in {acct}",
            "detail": "it happened at the grocery store and it was so embarrassing in front of everyone in line",
        },
    ],
    opportunities=[
        {
            "type": "High-yield savings interest",
            "open": "i heard meridian has a new high yield savings account is that something i could move my money into",
            "detail": "i currently have about {amount} just sitting in a regular savings account earning almost nothing",
        },
        {
            "type": "Joint account / relationship banking",
            "open": "my partner and i are moving in together and want to open a joint checking account",
            "detail": "do you have any bundled rates if we also move our savings over to meridian",
        },
        {
            "type": "Student account referral",
            "open": "my daughter is starting college in the fall and i wanted to ask about a student checking account",
            "detail": "does it come with no monthly fees while shes still enrolled",
        },
    ],
    neutral=[
        {
            "topic": "Address update",
            "open": "i need to update my mailing address on my checking account",
            "detail": "i just moved to a new place last week and want my statements sent there",
        },
        {
            "topic": "Statement request",
            "open": "can you send me a copy of my statement from last {date_ref}",
            "detail": "i need it for my taxes and i can not find it in the app",
        },
    ],
)

# ---------------------------------------------------------------------------
# Credit Cards
# ---------------------------------------------------------------------------
register(
    "Credit Cards",
    "CARDS",
    complaints=[
        {
            "category": "APR / interest rate dispute",
            "open": "my a p r jumped to {rate} percent and nobody sent me a notice about it",
            "detail": "i have never missed a payment in {count} years so i dont understand why my rate went up",
        },
        {
            "category": "Billing error",
            "open": "there is a charge on my statement for {amount} that i never made",
            "detail": "i already called once about this last {date_ref} and it still has not been fixed",
        },
        {
            "category": "Rewards program issue",
            "open": "my cash back rewards disappeared from my account and i had almost {amount} saved up",
            "detail": "the app just shows zero now and i have no idea where the points went",
        },
        {
            "category": "Late fee dispute",
            "open": "i got hit with a late fee of {fee} but i made the payment on time through the app",
            "detail": "i have a screenshot showing the payment went through on {date_ref}",
        },
    ],
    opportunities=[
        {
            "type": "Balance transfer offer",
            "open": "i have about {amount} in credit card debt on another card with a really high rate",
            "detail": "do you guys do balance transfers with a promotional rate for meridian customers",
        },
        {
            "type": "Credit limit increase / premium card upgrade",
            "open": "i wanted to ask about upgrading to one of your premium travel cards",
            "detail": "i travel for work pretty often and want better rewards on flights and hotels",
        },
    ],
    neutral=[
        {
            "topic": "PIN reset",
            "open": "i forgot the pin on my credit card and need to reset it",
            "detail": "i tried the atm twice already and it locked me out",
        },
        {
            "topic": "Travel notice",
            "open": "i am traveling to europe next {date_ref} and want to put a travel notice on my card",
            "detail": "i dont want it declined when i am overseas",
        },
    ],
)

# ---------------------------------------------------------------------------
# Mortgage & Home Lending
# ---------------------------------------------------------------------------
register(
    "Mortgage & Home Lending",
    "MORTGAGE",
    complaints=[
        {
            "category": "Escrow shortage",
            "open": "i got a letter saying my escrow is short by {amount} and my monthly payment is going up",
            "detail": "nobody explained why property taxes went up this much in just one year",
        },
        {
            "category": "Refinance delay",
            "open": "i started my refinance application over {days} days ago and havent heard anything back",
            "detail": "i have called three times and every time i get a different answer about the status",
        },
        {
            "category": "Closing cost surprise",
            "open": "the closing costs on my loan were about {amount} more than what i was originally quoted",
            "detail": "i feel like this changed at the last minute right before closing",
        },
        {
            "category": "Payment processing error",
            "open": "i made my mortgage payment on {date_ref} but it still shows as late on my account",
            "detail": "now i am worried this is going to hurt my credit score",
        },
    ],
    opportunities=[
        {
            "type": "Refinance interest",
            "open": "i saw rates have come down and wanted to ask about refinancing my current mortgage",
            "detail": "my current rate is {rate} percent and i am hoping to lower my monthly payment",
        },
        {
            "type": "Home equity line of credit",
            "open": "i have a lot of equity built up in my house and want to ask about a home equity line of credit",
            "detail": "i am looking to do a kitchen renovation for around {amount}",
        },
    ],
    neutral=[
        {
            "topic": "Escrow statement request",
            "open": "can i get a copy of my escrow analysis statement",
            "detail": "i just want to double check the numbers myself",
        },
        {
            "topic": "Payoff quote",
            "open": "i want to request a payoff quote on my mortgage",
            "detail": "we are thinking about selling the house later this year",
        },
    ],
)

# ---------------------------------------------------------------------------
# Auto Finance
# ---------------------------------------------------------------------------
register(
    "Auto Finance",
    "AUTO",
    complaints=[
        {
            "category": "Payment posting delay",
            "open": "i made my car payment of {amount} on {date_ref} and it still isnt showing up on my account",
            "detail": "i am worried i am going to get hit with a late fee even though i paid on time",
        },
        {
            "category": "Payoff amount dispute",
            "open": "the payoff amount you gave me is {amount} more than what i calculated on my own",
            "detail": "i want somebody to walk me through exactly how that number was calculated",
        },
        {
            "category": "Title / lien release delay",
            "open": "i paid off my auto loan {days} days ago and i still have not received the title release",
            "detail": "i need that document to sell the car and the buyer is getting impatient",
        },
    ],
    opportunities=[
        {
            "type": "Auto refinance",
            "open": "i financed my car through the dealership at a really high rate and want to refinance",
            "detail": "my rate right now is {rate} percent which feels way too high",
        },
        {
            "type": "New vehicle loan pre-approval",
            "open": "i am shopping for a new car and wanted to get pre approved for an auto loan through meridian",
            "detail": "i am looking to finance around {amount}",
        },
    ],
    neutral=[
        {
            "topic": "Insurance info update",
            "open": "i need to update the insurance information on file for my auto loan",
            "detail": "i just switched providers last {date_ref}",
        },
    ],
)

# ---------------------------------------------------------------------------
# Small Business Banking
# ---------------------------------------------------------------------------
register(
    "Small Business Banking",
    "SMB",
    complaints=[
        {
            "category": "Merchant services fees",
            "open": "our merchant processing fees went up again and nobody from meridian gave us a heads up",
            "detail": "we are a small shop and these fees are eating into our margin every month",
        },
        {
            "category": "Business loan delay",
            "open": "we applied for a small business line of credit over {days} days ago and still have no decision",
            "detail": "we need this to make payroll and the delay is putting real stress on the business",
        },
        {
            "category": "Wire transfer issue",
            "open": "we sent a wire for {amount} to a supplier and it still has not arrived after {days} days",
            "detail": "our supplier is threatening to hold our shipment because they havent been paid",
        },
    ],
    opportunities=[
        {
            "type": "Business line of credit",
            "open": "we are growing pretty fast and wanted to ask about a business line of credit",
            "detail": "we are looking for something around {amount} to cover inventory during our busy season",
        },
        {
            "type": "Payroll / treasury services",
            "open": "we are outgrowing our current payroll setup and heard meridian has treasury management services",
            "detail": "we have about {count} employees right now and growing",
        },
    ],
    neutral=[
        {
            "topic": "New business account setup",
            "open": "we just got our llc paperwork finalized and want to open a business checking account",
            "detail": "what documents do we need to bring in to get that set up",
        },
    ],
)

# ---------------------------------------------------------------------------
# Fraud & Disputes
# ---------------------------------------------------------------------------
register(
    "Fraud & Disputes",
    "FRAUD",
    complaints=[
        {
            "category": "Unauthorized transaction",
            "open": "there are charges on my account i did not make totaling almost {amount}",
            "detail": "i think my card information got stolen because i have never even been to that store",
        },
        {
            "category": "Account takeover concern",
            "open": "i got a notification that my password was changed but i never changed it",
            "detail": "i am really worried someone else has access to my account right now",
        },
        {
            "category": "Dispute resolution delay",
            "open": "i filed a dispute for {amount} over {days} days ago and still have no update",
            "detail": "the provisional credit i was told about never even showed up in my account",
        },
        {
            "category": "Phishing / scam victim",
            "open": "i think i got scammed after clicking a link in a text message that looked like it was from meridian",
            "detail": "i gave them my login information before i realized something was wrong",
        },
    ],
    opportunities=[
        {
            "type": "Identity protection / alerts upsell",
            "open": "after what happened i want to ask what extra fraud protection or account alerts meridian offers",
            "detail": "i want to make sure i get a text the second anything unusual happens on my account",
        },
    ],
    neutral=[
        {
            "topic": "Card lock/unlock",
            "open": "i misplaced my card and want to lock it temporarily while i look for it",
            "detail": "i found it already actually, can you unlock it again",
        },
    ],
)


def fill(template, rng):
    return template.format(
        app=APP_NAME,
        bank=BANK_NAME,
        fee=f"${_rand_amount(25, 45, rng):.2f}",
        amount=f"${_rand_amount(150, 18000, rng):,.2f}",
        rate=f"{_rand_amount(4.5, 27.9, rng):.1f}",
        days=rng.randint(3, 45),
        count=rng.randint(2, 9),
        wait=rng.randint(15, 55),
        acct=f"{rng.randint(1000, 9999)}",
        date_ref=rng.choice(
            ["monday", "tuesday", "last week", "the 3rd", "the 14th", "this past weekend", "yesterday"]
        ),
    )
