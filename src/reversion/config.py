from django.conf import settings


AUDIT_LOG_SHORT_COMMENT_LENGTH = getattr(settings, 'AUDIT_LOG_SHORT_COMMENT_LENGTH', 130)
