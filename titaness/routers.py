class WikipediaRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "wikipediaapp":
            return "wikipedia"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "wikipediaapp":
            return "wikipedia"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == "wikipediaapp" and obj2._meta.app_label == "wikipediaapp":
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "wikipediaapp":
            return db == "wikipedia"
        return None
