"""Roles (身分): what a user may see and manage beyond their own datasets.

Two are built in and cannot be deleted: ``admin`` (everything, always) and
``user`` (the default for new accounts; its permissions can be changed).
Admins add their own (e.g. 助教) with any mix of PERMISSIONS."""
from mongoengine import DynamicDocument, StringField, ListField, BooleanField, IntField

# roles saved before a permission existed that everyone used to have get it once
# (rev 1: create_categories)
PERM_REV = 1
_migrated = False

# pages first, then management rights
PAGES = ('activity', 'models', 'tasks')
# create_categories: make new categories (category page, new names typed for a
# dataset, classes a model or an import finds); manage_categories: change and
# delete every category, not only one's own (and see them all)
# train: start YOLO trainings on the server; terminal: the web SSH terminal
MANAGE = ('create_categories', 'manage_categories', 'manage_models', 'manage_users', 'all_datasets',
          'train', 'terminal')
PERMISSIONS = PAGES + MANAGE
# what every account could always do: a user manager may give it without having it
BASIC = ('create_categories',)

ADMIN = 'admin'
DEFAULT = 'user'


def available():
    """The permissions in use: the web terminal only when TERMINAL_ENABLED."""
    from config import Config
    return tuple(p for p in PERMISSIONS if p != 'terminal' or Config.TERMINAL_ENABLED)


class RoleModel(DynamicDocument):
    key = StringField(primary_key=True)
    name = StringField(default='')
    permissions = ListField(StringField(), default=list)
    builtin = BooleanField(default=False)
    order = IntField(default=100)
    perm_rev = IntField(default=PERM_REV)

    meta = {'collection': 'role_model'}

    @staticmethod
    def clean_permissions(perms):
        return [p for p in available() if p in (perms or [])]

    @classmethod
    def migrate(cls):
        """Everyone could make categories before it was a permission: roles
        from then keep that (once; an admin can take it away afterwards)."""
        global _migrated
        if _migrated:
            return
        for role in cls.objects(perm_rev__exists=False):
            perms = list(role.permissions or [])
            if 'create_categories' not in perms:
                perms.append('create_categories')
            role.update(set__permissions=perms, set__perm_rev=PERM_REV)
        _migrated = True

    @classmethod
    def ensure_builtin(cls):
        cls.migrate()
        if cls.objects(key=ADMIN).first() is None:
            cls(key=ADMIN, name='', permissions=list(PERMISSIONS), builtin=True, order=0).save()
        if cls.objects(key=DEFAULT).first() is None:
            cls(key=DEFAULT, name='', permissions=['create_categories'], builtin=True, order=1).save()

    @classmethod
    def all_ordered(cls):
        cls.ensure_builtin()
        return list(cls.objects.order_by('order', 'name'))

    @classmethod
    def permissions_of(cls, key):
        if not _migrated:
            cls.ensure_builtin()
        if key == ADMIN:
            return set(available())
        role = cls.objects(key=key or DEFAULT).first() or cls.objects(key=DEFAULT).first()
        return set(role.permissions or []) & set(available()) if role else set()

    def to_dict(self, users=None):
        out = {'key': self.key, 'name': self.name or '', 'builtin': bool(self.builtin),
               'permissions': self.clean_permissions(self.permissions) if self.key != ADMIN else list(available())}
        if users is not None:
            out['users'] = users
        return out
