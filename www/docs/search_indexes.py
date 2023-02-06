import datetime
from haystack import indexes
from docs.models import Document
from django.utils.timezone import make_aware


class DocumentIndex(indexes.SearchIndex, indexes.Indexable):
    text        = indexes.CharField(document=True, use_template=True,verbose_name='Recherche')
    record_date = indexes.DateTimeField(model_attr='record_date')
    domain      = indexes.CharField(model_attr='domain')
    doc_type    = indexes.CharField(model_attr='doc_type')

    def get_model(self):
        return Document

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(record_date__lte=make_aware(datetime.datetime.now()))