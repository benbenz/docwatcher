from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Document(models.Model):

    class DocumentType(models.TextChoices):
        UNKNOWN   = 'UNK', _('Unknown')
        TEXT      = 'TXT', _('Text')
        RTF       = 'RTF', _('Rich Text Format')
        HTML      = 'HTML', _('HTML')
        PDF       = 'PDF', _('PDF')
        DOC       = 'DOC', _('Doc')
        DOCX      = 'DOCX', _('Docx')
        PPT       = 'PPT', _('PowerPoint')
        PPTX      = 'PPTX', _('PowerPointX')
        PPTM      = 'PPTM', _('PowerPointM')

    #user = models.ForeignKey(User)

    # Crawl information
    domain      = models.CharField(max_length=100,db_index=True)
    url         = models.URLField(max_length=200,db_index=True)
    final_url   = models.URLField(max_length=200,db_index=True,null=True)
    #referer     = models.URLField(max_length=200,db_index=True)
    referers    = models.ManyToManyField('self', related_name='links', symmetrical=False, blank=True, through='Sitemap')
    #depth       = models.IntegerField()
    record_date = models.DateTimeField(auto_now_add=True, blank=True)
    remote_name = models.CharField(max_length=200)

    # HTTP headers
    http_length        = models.IntegerField()
    http_encoding      = models.CharField(max_length=32)
    http_last_modified = models.DateTimeField(null=True,blank=True)
    http_content_type  = models.CharField(max_length=64)

    # Content: HTML/PDF + file
    local_file  = models.FilePathField(unique=True,db_index=True)    
    doc_type    = models.CharField(max_length=4,choices=DocumentType.choices,default=DocumentType.TEXT)    
    title       = models.CharField(max_length=200)
    body        = models.TextField()
    num_pages   = models.IntegerField()
    size        = models.IntegerField()
    needs_ocr   = models.BooleanField()
    has_error   = models.BooleanField()
    file_status = models.SmallIntegerField()
    of_interest = models.BooleanField()

    def get_absolute_url(self):
        return "/docs/%i/" % self.id      

class Sitemap(models.Model):
    referer = models.ForeignKey(Document, related_name='referer_docs', on_delete=models.CASCADE)
    link    = models.ForeignKey(Document, related_name='link_docs'   , on_delete=models.CASCADE)
    depth   = models.IntegerField()

class DocumentSearch(models.Model):

    params = models.JSONField("SearchParams",unique=True)
    hits   = models.ManyToManyField('Document', related_name='searches', symmetrical=False, blank=True)
