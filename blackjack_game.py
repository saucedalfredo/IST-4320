import random
import sys

# Tkinter draws the window. Some Python installs are missing it — we show a clear error.
try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError as err:
    print("ERROR: tkinter is not available for this Python install.\n")
    print("The game needs tkinter to open a window.\n")
    print("Try one of these fixes:")
    print("  • macOS (Homebrew Python): in Terminal run  brew install python-tk")
    print("  • Or install Python from https://www.python.org/downloads/ (includes tkinter)")
    print("  • Then run:  python3 blackjack_game.py")
    print()
    print("Technical detail:", err)
    sys.exit(1)


# --- Game constants ---
STARTING_BALANCE = 500
BET_AMOUNTS = [5, 10, 25, 50, 100]

# --- Card deck for random dealing (simplified infinite deck) ---
CARD_RANKS = [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "J",
    "Q",
    "K",
    "A",
]


def deal_card():
    """Pick one random card from CARD_RANKS."""
    return random.choice(CARD_RANKS)


def calculate_total(hand):
    """
    Add up card values for the hand (simplified Blackjack).
    Face cards (J, Q, K) = 10. Ace = 11. Numbers use printed value.
    """
    total = 0
    for card in hand:
        if card in ("J", "Q", "K"):
            total += 10
        elif card == "A":
            total += 11
        else:
            total += int(card)
    return total


def compare_hands(player_total, dealer_total):
    """
    Return who wins when neither bust earlier: 'player', 'dealer', or 'push'.
    Dealer bust (>21) is handled before calling this.
    """
    if dealer_total > 21:
        return "player"
    if player_total > dealer_total:
        return "player"
    if dealer_total > player_total:
        return "dealer"
    return "push"


def update_balance_display():
    """Refresh the dollar balance shown at the top."""
    lbl_balance.config(text=f"Balance: ${balance}")


def update_bet_hint():
    """Show how much money is wagered during an active hand."""
    if game_over:
        lbl_bet_amt.config(text="")
    else:
        lbl_bet_amt.config(text=f"Bet this hand: ${hand_wager}")


def update_display():
    """
    Refresh card labels using the game state.
    While the player is still playing, the dealer's hole card stays hidden.
    """
    player_cards_text = " ".join(player_hand)
    player_total = calculate_total(player_hand)
    lbl_player_cards.config(text=f"Cards: {player_cards_text}")
    lbl_player_total.config(text=f"Total: {player_total}")

    if dealer_hole_hidden and len(dealer_hand) >= 2:
        shown = dealer_hand[0]
        lbl_dealer_cards.config(text=f"Cards: {shown} ?")
        lbl_dealer_total.config(text="Total: ?")
    else:
        dealer_cards_text = " ".join(dealer_hand)
        dealer_total = calculate_total(dealer_hand)
        lbl_dealer_cards.config(text=f"Cards: {dealer_cards_text}")
        lbl_dealer_total.config(text=f"Total: {dealer_total}")


def set_betting_controls_enabled(enabled):
    """Turn wager choices + Deal on (with affordability checks) or all off."""
    if not enabled:
        for btn in wager_buttons.values():
            btn.config(state=tk.DISABLED)
        btn_deal.config(state=tk.DISABLED)
        return

    # Hand is over — let the player bet again within their balance.
    can_bet_any = False
    for amount, btn in wager_buttons.items():
        if balance >= amount:
            btn.config(state=tk.NORMAL)
            can_bet_any = True
        else:
            btn.config(state=tk.DISABLED)

    # If balance is smaller than every chip size, Deal must stay disabled.
    if not can_bet_any:
        btn_deal.config(state=tk.DISABLED)
        lbl_status.config(
            text="You're out of money! Press Restart Game to get "
            f"${STARTING_BALANCE} again."
        )
        lbl_status_line2.config(text="")
        return

    amt = selected_bet_var.get()
    if amt not in wager_buttons or balance < amt:
        for try_amt in BET_AMOUNTS:
            if balance >= try_amt:
                amt = try_amt
                break
        selected_bet_var.set(amt)

    select_wager(selected_bet_var.get())

    btn_deal.config(state=tk.NORMAL)


def set_player_action_buttons(playing_is_on):
    """Hit / Stand / Double only while the player finishes their turn."""
    if playing_is_on:
        btn_hit.config(state=tk.NORMAL)
        btn_stand.config(state=tk.NORMAL)
        # Double down: only two starting cards (or after doubling you auto-stand)
        can_dd = (
            len(player_hand) == 2
            and not doubled_this_hand
            and balance >= hand_wager  # player must afford the extra matching bet
        )
        btn_double.config(state=tk.NORMAL if can_dd else tk.DISABLED)
    else:
        btn_hit.config(state=tk.DISABLED)
        btn_stand.config(state=tk.DISABLED)
        btn_double.config(state=tk.DISABLED)


def select_wager(amount):
    """Remember which chip the player picked and update how the buttons look."""
    selected_bet_var.set(amount)
    for amt, btn in wager_buttons.items():
        if btn.cget("state") != tk.DISABLED:
            btn.config(relief=tk.SUNKEN if amt == amount else tk.RAISED)
    if game_over and balance >= amount:
        btn_deal.config(state=tk.NORMAL)
    elif game_over:
        btn_deal.config(state=tk.DISABLED)


def settle_hand(result, extra_note=""):
    """
    Pay out (or not) now that the hand is over and show a clear money message.
    result is 'win', 'lose', or 'push'. extra_note is an optional subtitle line.
    """
    global balance, game_over

    if result == "win":
        payout = hand_wager * 2
        balance += payout
        msg = (
            f"You win! Profit +${hand_wager}  "
            f"(paid back ${payout} total, including your bet)  "
            f"Balance: ${balance}"
        )
    elif result == "push":
        balance += hand_wager
        msg = (
            f"Push — tie game. Your ${hand_wager} bet returned.  "
            f"Balance: ${balance}"
        )
    else:
        msg = f"You lose. Lost ${hand_wager}.  Balance: ${balance}"

    lbl_status.config(text=msg)
    lbl_status_line2.config(text=extra_note)

    update_balance_display()
    update_bet_hint()

    game_over = True
    set_player_action_buttons(False)
    set_betting_controls_enabled(True)


def dealer_play_and_finish():
    """
    Reveal dealer, draw until 17+, decide winner, settle money at the end.
    """
    global dealer_hole_hidden

    dealer_hole_hidden = False
    update_display()

    while calculate_total(dealer_hand) < 17:
        dealer_hand.append(deal_card())
        update_display()

    pt = calculate_total(player_hand)
    dt = calculate_total(dealer_hand)
    outcome = compare_hands(pt, dt)

    if outcome == "player":
        if dt > 21:
            note = f"The dealer busts with {dt}."
        else:
            note = f"You have {pt} and the dealer has {dt}."
        settle_hand("win", note)
    elif outcome == "dealer":
        settle_hand("lose", f"Dealer finishes with {dt} beating your {pt}.")
    else:
        settle_hand("push", f"Both scored {pt}.")


def on_deal():
    """Start a new hand after picking a wager. Money leaves balance right away."""
    global player_hand, dealer_hand, dealer_hole_hidden, game_over
    global hand_wager, doubled_this_hand, balance

    if not game_over:
        return

    pick = selected_bet_var.get()
    if balance < pick:
        lbl_status.config(text=f"Not enough balance for ${pick}. Pick a smaller bet.")
        lbl_status_line2.config(text="")
        return

    hand_wager = pick
    doubled_this_hand = False

    balance -= hand_wager

    player_hand = [deal_card(), deal_card()]
    dealer_hand = [deal_card(), deal_card()]
    dealer_hole_hidden = True
    game_over = False

    lbl_status.config(text="Your turn — Hit, Stand, or Double Down.")
    lbl_status_line2.config(text="")

    update_balance_display()
    update_bet_hint()
    update_display()

    set_betting_controls_enabled(False)
    set_player_action_buttons(True)


def on_hit():
    """Draw one more card for the player; bust ends the hand immediately."""
    global game_over, dealer_hole_hidden

    if game_over:
        return

    player_hand.append(deal_card())
    update_display()

    # After a hit, double down is no longer allowed (more than two cards)
    set_player_action_buttons(True)

    total = calculate_total(player_hand)
    if total > 21:
        dealer_hole_hidden = False
        update_display()
        settle_hand("lose", f"You bust with {total}.")


def on_stand():
    """Player stops drawing; dealer plays out and we compare."""
    if game_over:
        return

    lbl_status.config(text="Dealer's turn…")
    dealer_play_and_finish()


def on_double_down():
    """
    Double the bet: take one more card only, then stand automatically.
    Player must have enough balance to match the current bet again.
    """
    global balance, hand_wager, doubled_this_hand, dealer_hole_hidden, game_over

    if game_over:
        return
    if len(player_hand) != 2 or doubled_this_hand:
        return
    if balance < hand_wager:
        return

    # Take the extra wager and double the hand's total bet
    balance -= hand_wager
    hand_wager *= 2
    doubled_this_hand = True

    update_balance_display()
    update_bet_hint()

    player_hand.append(deal_card())
    update_display()
    set_player_action_buttons(False)

    total = calculate_total(player_hand)
    if total > 21:
        dealer_hole_hidden = False
        update_display()
        lbl_status.config(text="Doubled — you drew one card.")
        settle_hand("lose", f"You bust with {total} after doubling.")
    else:
        lbl_status.config(
            text=f"Doubled! Bet is ${hand_wager}. You drew one card ({total}); dealer plays."
        )
        lbl_status_line2.config(text="")
        dealer_play_and_finish()


def on_restart():
    """Full reset — money back to the starting allowance and refresh the UI."""
    global balance, player_hand, dealer_hand, dealer_hole_hidden, game_over
    global hand_wager, doubled_this_hand

    balance = STARTING_BALANCE
    player_hand = []
    dealer_hand = []
    dealer_hole_hidden = False
    game_over = True
    hand_wager = 0
    doubled_this_hand = False

    lbl_player_cards.config(text="Cards:")
    lbl_player_total.config(text="Total:")
    lbl_dealer_cards.config(text="Cards:")
    lbl_dealer_total.config(text="Total:")
    lbl_status.config(text=f"Restarted bankroll to ${STARTING_BALANCE}. Pick a wager, then Deal.")
    lbl_status_line2.config(text="")

    update_balance_display()
    update_bet_hint()
    set_betting_controls_enabled(True)
    set_player_action_buttons(False)


# --- GUI setup ---
try:
    root = tk.Tk()
except tk.TclError as err:
    print("ERROR: The game window could not open.\n")
    print("Technical detail:", err)
    sys.exit(1)

root.title("Blackjack Game")
root.geometry("640x560")
root.resizable(False, False)

title_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
body_font = tkfont.Font(family="Helvetica", size=12)
small_font = tkfont.Font(family="Helvetica", size=11)

frm = tk.Frame(root, padx=16, pady=14)
frm.pack(fill=tk.BOTH, expand=True)

tk.Label(frm, text="Blackjack (with bets)", font=title_font).pack(anchor="w")

lbl_balance = tk.Label(frm, text="", font=body_font)
lbl_balance.pack(anchor="w", pady=(6, 0))

lbl_bet_amt = tk.Label(frm, text="", font=small_font, fg="#444444")
lbl_bet_amt.pack(anchor="w")

# --- Chip row ---
tk.Label(frm, text="Pick your wager:", font=body_font).pack(anchor="w", pady=(10, 4))
bet_row = tk.Frame(frm)
bet_row.pack(anchor="w")

selected_bet_var = tk.IntVar(master=root, value=25)
wager_buttons = {}

for amt in BET_AMOUNTS:
    b = tk.Button(
        bet_row,
        text=f"${amt}",
        font=body_font,
        width=7,
        command=lambda a=amt: select_wager(a),
    )
    b.pack(side=tk.LEFT, padx=(0, 6))
    wager_buttons[amt] = b

btn_deal = tk.Button(bet_row, text="Deal Hand", font=body_font, width=12, command=on_deal)
btn_deal.pack(side=tk.LEFT, padx=(18, 0))

tk.Label(frm, text="Your hand", font=body_font).pack(anchor="w", pady=(14, 0))
lbl_player_cards = tk.Label(frm, text="Cards:", font=body_font)
lbl_player_cards.pack(anchor="w")
lbl_player_total = tk.Label(frm, text="Total:", font=body_font)
lbl_player_total.pack(anchor="w")

tk.Label(frm, text="Dealer", font=body_font).pack(anchor="w", pady=(12, 0))
lbl_dealer_cards = tk.Label(frm, text="Cards:", font=body_font)
lbl_dealer_cards.pack(anchor="w")
lbl_dealer_total = tk.Label(frm, text="Total:", font=body_font)
lbl_dealer_total.pack(anchor="w")

lbl_status = tk.Label(frm, text="", font=body_font, fg="#222222")
lbl_status.pack(anchor="w", pady=(14, 0))

lbl_status_line2 = tk.Label(frm, text="", font=small_font, fg="#333333")
lbl_status_line2.pack(anchor="w")

btn_row = tk.Frame(frm)
btn_row.pack(anchor="w", pady=(10, 0))

btn_hit = tk.Button(btn_row, text="Hit", font=body_font, width=10, command=on_hit)
btn_hit.pack(side=tk.LEFT, padx=(0, 8))

btn_stand = tk.Button(btn_row, text="Stand", font=body_font, width=10, command=on_stand)
btn_stand.pack(side=tk.LEFT, padx=(0, 8))

btn_double = tk.Button(
    btn_row, text="Double Down", font=body_font, width=12, command=on_double_down
)
btn_double.pack(side=tk.LEFT, padx=(0, 8))

btn_restart = tk.Button(
    btn_row, text="Restart Game", font=body_font, width=12, command=on_restart
)
btn_restart.pack(side=tk.LEFT)

# --- Shared state ---
balance = STARTING_BALANCE
player_hand = []
dealer_hand = []
dealer_hole_hidden = False
game_over = True  # waits for Deal
hand_wager = 0
doubled_this_hand = False

update_balance_display()
lbl_status.config(text="Pick how much you want to bet, then press Deal.")
set_player_action_buttons(False)
set_betting_controls_enabled(True)

root.mainloop()


# 1. You start with $500. Pick a chip amount, press Deal Hand, then play.
#    • Double Down doubles your bet and gives exactly one more card,
#      then the dealer plays.
#    • Restart Game puts your bankroll back to $500.
#
# Rules: face cards = 10, Ace = 11, dealer hits to 17. Even money on wins.
# -----------------------------------------------------------------------------
