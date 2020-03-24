"""Module defining non-edit forms and widgets."""

from django import forms
from eats.models import Authority


class SearchForm (forms.Form):
    authorities = [(a.id, a.authority)
                   for a in Authority.objects.order_by('authority')]
    name = forms.CharField(max_length=200, required=False)
    authority = forms.ChoiceField(choices=authorities, required=False)
    record_id = forms.CharField(max_length=200, required=False,
                                label='Record ID')
    record_url = forms.CharField(max_length=400, required=False,
                                 label='Record URL')

    def clean(self):
        if not (self.data.get('name') or
                (self.data.get('authority') and
                 (self.data.get('record_id') or self.data.get('record_url')))):
            raise forms.ValidationError(
                'Either a name or an authority with either an ID or URL is required.')
        return self.cleaned_data
