from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# row = {
#     'filename': filename,
#     'local_name': local_name,
#     'url': response.url,
#     'linking_page_url': previous_url or '',
#     'size': response.headers.get('Content-Length') or '',
#     'depth': depth,
# }

# Create your models here.
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

    # Fetch information
    domain      = models.CharField(max_length=100)
    url         = models.URLField(max_length=200)
    referer     = models.URLField(max_length=200)
    depth       = models.IntegerField()
    record_date = models.DateTimeField(auto_now_add=True, blank=True)
    remote_name = models.CharField(max_length=200)

    # Content: HTML/PDF + file
    local_file  = models.FileField()    
    doc_type    = models.CharField(max_length=4,choices=DocumentType.choices,default=DocumentType.TEXT)    
    title       = models.CharField(max_length=200)
    body        = models.TextField()
    num_pages   = models.IntegerField()
    size        = models.IntegerField()
