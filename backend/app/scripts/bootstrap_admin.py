
from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


def main():
    email = input("Enter registered email: ").strip().lower()

    if input("Type PROMOTE to continue: ").strip() != "PROMOTE":
        print("Cancelled.")
        return

    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:
            print("Account not found. Registered accounts:")
            users = db.scalars(
                select(User).order_by(User.id)
            ).all()

            for account in users:
                print(
                    f"ID: {account.id} | "
                    f"Email: {account.email} | "
                    f"Role: {account.role}"
                )
            return

        if not user.is_active:
            print("Account is inactive. Activate it first.")
            return

        if user.role == "admin":
            print(f"{user.email} is already an administrator.")
            return

        user.role = "admin"
        db.commit()

        print(f"SUCCESS: {user.email} is now an administrator.")

    except Exception as exc:
        db.rollback()
        print("Failed to promote account:", exc)

    finally:
        db.close()


if __name__ == "__main__":
    main()
