/**
 * Account control for the navigation bar.
 *
 * Closed by default: a plain label that opens a small panel with the account
 * details, a way back into the screening from the top of the page, and sign-out.
 *
 * Keyboard behaviour is the reason this is its own component. The trigger is a
 * real button with aria-expanded, so Escape, arrow keys and Tab all work without
 * a focus trap: Tab leaves the panel the moment the last item is passed, which
 * is the behaviour a menu should have. Clicking elsewhere closes it, which is
 * handled by a listener on the document rather than on the panel, so the click
 * that dismisses also lands on whatever was clicked underneath.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAccount, useSignOut } from "../../lib/authContext";
import { clearCheckIn } from "../../lib/checkin";

/**
 * The two account actions, shared by the dropdown and the mobile menu.
 *
 * Both surfaces need them and only one of them can own the panel, so the
 * behaviour lives here rather than being written twice.
 */
export function useAccountActions() {
  const signOut = useSignOut();
  const navigate = useNavigate();

  const restartScreening = useCallback(() => {
    // Clear the saved check-in so restarting really starts from step one
    // instead of prefilling the previous answers.
    clearCheckIn();
    navigate("/screen");
  }, [navigate]);

  const logOut = useCallback(() => {
    signOut();
    navigate("/login", { replace: true });
  }, [signOut, navigate]);

  return { restartScreening, logOut };
}

export function AccountMenu() {
  const account = useAccount();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { restartScreening, logOut } = useAccountActions();

  const close = useCallback((returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) triggerRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(true);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  // Signing out changes the account, so there is nothing left to show.
  if (!account) return null;

  /**
   * Arrow-key movement between the panel's items.
   *
   * Required by the menu role: assistive technology announces these as menu
   * items and expects Up/Down to move between them. Tab is left alone on
   * purpose, so the panel does not become a focus trap.
   */
  const onMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const keys = ["ArrowDown", "ArrowUp", "Home", "End"];
    if (!keys.includes(event.key)) return;
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>("[role='menuitem']")
    );
    if (items.length === 0) return;
    event.preventDefault();
    const at = items.indexOf(document.activeElement as HTMLButtonElement);
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : event.key === "ArrowDown"
            ? (at + 1 + items.length) % items.length
            : (at - 1 + items.length) % items.length;
    items[next]?.focus();
  };

  return (
    <div className="account" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="account__trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls="account-menu"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="account__hello">
          Hello, <span className="account__name">{account.firstName}</span>
        </span>
        <svg
          className={`account__caret ${open ? "account__caret--open" : ""}`}
          viewBox="0 0 10 6"
          width="9"
          height="6"
          aria-hidden="true"
        >
          <path
            d="M1 1l4 4 4-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {open && (
        <div className="account__menu" id="account-menu" role="menu" onKeyDown={onMenuKeyDown}>
          <div className="account__id">
            {/* Full name here rather than the truncated greeting, so a long
                name is still readable in one piece. */}
            <p className="account__full">{account.name}</p>
            <p className="account__mail">{account.user}</p>
          </div>
          <button
            type="button"
            role="menuitem"
            className="account__item"
            onClick={() => {
              setOpen(false);
              restartScreening();
            }}
          >
            Restart screening
          </button>
          <button
            type="button"
            role="menuitem"
            className="account__item"
            onClick={() => {
              setOpen(false);
              logOut();
            }}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}