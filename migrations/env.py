import sys
import os

# CRUCIALE FIX: Voeg de root directory van het project toe aan sys.path
# Dit zorgt ervoor dat Python de 'run' module kan vinden.
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), ".")))

# Importeer de app nu de root in het pad zit.
from run import create_app  
import logging
from logging.config import fileConfig

# NIEUWE FIX: Importeer ALLE modellen zodat Alembic ze kan vergelijken met de DB
from app.models import Profile, Company, Project, Features_ideas, Roadmap, Milestone, Evidence, Decision

from flask import current_app

from alembic import context

# Instantieer de app hier. De configuratie wordt geladen bij het creëren.
app = create_app()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# ====================================================================
# HELPER FUNCTIONS
# ====================================================================

def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


def get_metadata():
    target_db = current_app.extensions["migrate"].db
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


# ====================================================================
# MIGRATION MODES
# ====================================================================

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=get_metadata(), literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.
    """

    # CRUCIALE WIJZIGING: Plaats de Alembic-logica binnen de Flask app context
    with app.app_context(): 
        
        # Stel de DB URL in BINNEN de context, dit voorkomt de RuntimeError
        config.set_main_option("sqlalchemy.url", get_engine_url())
        
        # this callback is used to prevent an auto-migration from being generated
        # when there are no changes to the schema
        def process_revision_directives(context, revision, directives):
            if getattr(config.cmd_opts, "autogenerate", False):
                script = directives[0]
                if script.upgrade_ops.is_empty():
                    directives[:] = []
                    logger.info("No changes in schema detected.")

        conf_args = current_app.extensions["migrate"].configure_args
        if conf_args.get("process_revision_directives") is None:
            conf_args["process_revision_directives"] = process_revision_directives

        connectable = get_engine()

        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=get_metadata(), **conf_args
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()