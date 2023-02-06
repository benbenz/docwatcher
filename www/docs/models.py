from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from crawler.core import FileStatus 

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
    url         = models.URLField(max_length=254,db_index=True)
    final_url   = models.URLField(max_length=254,db_index=True,null=True,blank=True)
    referers    = models.ManyToManyField('self', related_name='links', symmetrical=False, blank=True)    
    record_date = models.DateTimeField(auto_now_add=True, blank=True)
    remote_name = models.CharField(max_length=128,default='')

    # HTTP headers
    http_length        = models.IntegerField(default=-1)
    http_encoding      = models.CharField(max_length=32,null=True,blank=True)
    http_last_modified = models.DateTimeField(null=True,blank=True)
    http_content_type  = models.CharField(max_length=64,null=True,blank=True)

    # Content: HTML/PDF + file
    local_file  = models.FilePathField(unique=True,db_index=True,null=True)    
    doc_type    = models.CharField(max_length=4,choices=DocumentType.choices,default=DocumentType.UNKNOWN)    
    title       = models.CharField(max_length=254,blank=True,null=True)
    body        = models.TextField(null=True,blank=True)
    num_pages   = models.IntegerField(default=-1)
    size        = models.IntegerField(default=-1)
    needs_ocr   = models.BooleanField(default=False)
    has_ocr     = models.BooleanField(default=False)
    has_error   = models.BooleanField(default=False)
    file_status = models.SmallIntegerField(default=FileStatus.UNKNOWN)
    of_interest = models.BooleanField(default=False)
    is_handled  = models.BooleanField(default=False)

    def get_absolute_url(self):
        return "/docs/%i/" % self.id      

class RecLinkedUrl(models.Model):
    referer = models.ForeignKey(Document, related_name='rec_links', on_delete=models.CASCADE)
    url     = models.URLField(max_length=200,db_index=True)

class DocumentSearch(models.Model):

    params = models.JSONField("SearchParams",unique=True)
    hits   = models.ManyToManyField('Document', related_name='searches', symmetrical=False, blank=True)
