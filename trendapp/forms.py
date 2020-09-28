import time

from django import forms

from dataapp.models import UserEx
from klangapp.models import ClusterResult
from lda.topics import topics_for_user
from trendapp.models import User


class TrendForm(forms.Form):
    schools = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple(), required=True)
    trend = forms.CharField(required=True)
    display_3d = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_schools()

    def fill_schools(self):
        start = time.time()
        top_tweeters = User.objects.top_tweeters()
        end = time.time()
        print(end - start)
        self.fields["schools"].choices = [(user.name, f"{user.name} - {user.num_tweets}") for user in top_tweeters]


class FrequencyForm(forms.Form):
    USER_LIMIT = 10

    users = forms.MultipleChoiceField(choices=(), widget=forms.SelectMultiple(attrs={
        "class": "selectpicker",
        "data-live-search": "true",
        "data-actions-box": "true",
        "data-max-options": 10
    }), required=True)
    term = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_users()

    def fill_users(self):
        users = UserEx.objects.all()
        self.fields["users"].choices = [(user.pk, user.screen_name) for user in users]


class TopicNodeForm(forms.Form):
    """
    Form to be used in the 2d topic nodes graph.
    """
    users = forms.MultipleChoiceField(choices=(), widget=forms.SelectMultiple(attrs={
        "class": "selectpicker",
        "data-live-search": "true",
        # "data-actions-box": "true",
        "data-max-options": 10
    }), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users = UserEx.objects.filter(screen_name__in=ClusterResult.objects.values_list("name", flat=True))
        self.fields["users"].choices = [(user.pk, user.screen_name) for user in users]


class LDASchoolForm(forms.Form):
    school = forms.ChoiceField(choices=(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_schools()

    def fill_schools(self):
        top_tweeters = User.objects.top_tweeters()
        self.fields["school"].choices = [(user.name, f"{user.name} - {user.num_tweets}") for user in top_tweeters]


class LDATrendForm(forms.Form):
    school = forms.CharField(widget=forms.HiddenInput)
    topic = forms.ChoiceField(choices=(), widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        topics = kwargs.pop("topics", None)
        super().__init__(*args, **kwargs)
        if topics:
            vals = [[x[0] for x in topic] for topic in topics]
            choices = [(";".join(x), " ".join(x)) for x in vals]
            self.fields["topic"].choices = choices

    def clean_school(self):
        data = self.cleaned_data["school"]
        # this is almost certainly one of the dumbest ways to fix this but it's the only one i have found after 2 hours
        # of experimenting
        topics = topics_for_user(data)
        vals = [[x[0] for x in topic] for topic in topics]
        choices = [(";".join(x), " ".join(x)) for x in vals]
        self.fields["topic"].choices = choices
        return data
