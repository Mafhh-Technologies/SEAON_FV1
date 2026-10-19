"""
SEAON ERP - One-click startup.

Run:
    python app.py

The startup order is important:
1. Configure Django.
2. Initialize the Django application registry.
3. Apply migrations.
4. Seed the demo administrator/roles.
5. Import supplied sample stock data.
6. Start the Django development server.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    # Django must be initialized before call_command() can access models/apps.
    import django

    django.setup()

    from django.core.management import call_command

    print("Preparing SEAON ERP...")

    call_command("migrate", interactive=False)
    call_command("seed_seaon")
    call_command("import_sample_data")

    print()
    print("========================================")
    print("       SEAON ERP IS STARTING")
    print("========================================")
    print()
    print("Open: http://127.0.0.1:8000/app/login.html")
    print("Login: admin@seaon.com")
    print("Password: Admin@123")
    print()
    print("Press CTRL+C to stop the server.")
    print()

    call_command("runserver", "127.0.0.1:8000")


if __name__ == "__main__":
    main()
