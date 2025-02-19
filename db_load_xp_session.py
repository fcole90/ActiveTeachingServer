import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "ActiveTeachingServer.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from user_data.db_operation import load_user_data
from teaching_material.db_operation import fill_kanji_table


def load_session(session):

    load_user_data(bkp_file=os.path.join(
        'data', session, 'user_and_question_tables.sql'
    ))

    fill_kanji_table(bkp_file=os.path.join(
        'data', session, 'kanji_table.sql'
    ))


load_session(session='Pilot20190902')
