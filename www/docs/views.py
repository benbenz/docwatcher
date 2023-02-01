from django.shortcuts import render
from django.http import HttpResponse
from .models import Document , DocumentSearch
from django.contrib.auth import authenticate
from django.http import Http404
import os
import logging
from django.contrib.auth.decorators import login_required
from django.conf import settings
logger = logging.getLogger("mylogger")

def index(request):
    return HttpResponse("Hello, world. You're at the doc index.")

@login_required(login_url=settings.LOGIN_URL)
def detail(request, doc_id):
    # if not request.user.is_authenticated:
    #     raise Http404("page does not exist") # we hide it as a does not exist ...
    try:
        document = Document.objects.get(pk=doc_id)
        cached_page = None
        if document.doc_type == Document.DocumentType.HTML:
            file_path = document.local_file
            if file_path:
                try:
                    with open(os.path.join(settings.BASE_DIR.parent,file_path),mode='r',encoding='utf-8') as f:
                        cached_page = f.read()
                except Exception as e:
                    logger.info(e)
    except Document.DoesNotExist:
        raise Http404("Document does not exist")
    return render(request, 'docs/detail.html', {'document': document,'cached_page':cached_page})    

@login_required(login_url=settings.LOGIN_URL)
def search_results(request, search_id):
    # if not request.user.is_authenticated:
    #     raise Http404("page does not exist") # we hide it as a does not exist ...
    try:
        search = DocumentSearch.objects.get(pk=search_id)
    except DocumentSearch.DoesNotExist:
        raise Http404("Document Search does not exist")
    return render(request, 'docs/search_detail.html', {'search': search})        

@login_required(login_url=settings.LOGIN_URL)
def all_searches(request):
    # if not request.user.is_authenticated:
    #     raise Http404("page does not exist") # we hide it as a does not exist ...
    searches = DocumentSearch.objects.all()
    return render(request, 'docs/all_searches.html', {'searches': searches})    

@login_required(login_url=settings.LOGIN_URL)
def search_result(request, search_id):
    # if not request.user.is_authenticated:
    #     raise Http404("page does not exist") # we hide it as a does not exist ...
    return HttpResponse("Search result page")

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.shortcuts import render

from haystack.forms import FacetedSearchForm, HighlightedModelSearchForm , ModelSearchForm
from haystack.query import EmptySearchQuerySet
from haystack.views import SearchView

RESULTS_PER_PAGE = getattr(settings, "HAYSTACK_SEARCH_RESULTS_PER_PAGE", 20)


class HighlightedSearchView(SearchView):
    # template = "search/highlighted_search.html"
    # extra_context = {}
    # query = ""
    # results = EmptySearchQuerySet()
    # request = None
    # form = None
    # results_per_page = RESULTS_PER_PAGE

    def __init__(
        self,
        template=None,
        load_all=True,
        form_class=None,
        searchqueryset=None,
        results_per_page=None,
    ):
        super().__init__(template='search/highlighted_search.html',
                        load_all=load_all,
                        form_class=HighlightedModelSearchForm,
                        searchqueryset=searchqueryset,
                        results_per_page=results_per_page)
        # self.load_all = load_all
        # self.form_class = form_class
        # self.searchqueryset = searchqueryset

        # if form_class is None:
        #     self.form_class = HighlightedModelSearchForm

        # if results_per_page is not None:
        #     self.results_per_page = results_per_page

        # if template:
        #     self.template = template

    # def __call__(self, request):
    #     """
    #     Generates the actual response to the search.

    #     Relies on internal, overridable methods to construct the response.
    #     """
    #     self.request = request

    #     self.form = self.build_form()
    #     self.query = self.get_query()
    #     self.results = self.get_results()
    #     # add highlighting
    #     self.results.highlight()

    #     for r in self.results:
    #         r.highlighted['text'][0] = r.highlighted['text'][0].replace("\n",'<br/>')
    #         logger.info(r.highlighted['text'][0])

    #     return self.create_response()
    def __call__(self,request):
        if not request.user.is_authenticated:
            raise Http404("woopsie") # we hide it as a does not exist ...
        return super().__call__(request)


    # def build_form(self, form_kwargs=None):
    #     """
    #     Instantiates the form the class should use to process the search query.
    #     """
    #     data = None
    #     kwargs = {"load_all": self.load_all}
    #     if form_kwargs:
    #         kwargs.update(form_kwargs)

    #     if len(self.request.GET):
    #         data = self.request.GET

    #     if self.searchqueryset is not None:
    #         kwargs["searchqueryset"] = self.searchqueryset

    #     return self.form_class(data, **kwargs)

    # def get_query(self):
    #     """
    #     Returns the query provided by the user.

    #     Returns an empty string if the query is invalid.
    #     """
    #     if self.form.is_valid():
    #         return self.form.cleaned_data["q"]

    #     return ""

    def get_results(self):
        """
        Fetches the results via the form.

        Returns an empty list if there's no query to search with.
        """
        results = super().get_results()

        for r in results:
            r.highlighted['text'][0] = r.highlighted['text'][0].replace("\\n",'<br/>')
            r.highlighted['text'][0] = r.highlighted['text'][0].replace("\n",'<br/>')
            logger.info(r.highlighted['text'][0])
        
        return results 


    # def build_page(self):
    #     """
    #     Paginates the results appropriately.

    #     In case someone does not want to use Django's built-in pagination, it
    #     should be a simple matter to override this method to do what they would
    #     like.
    #     """
    #     try:
    #         page_no = int(self.request.GET.get("page", 1))
    #     except (TypeError, ValueError):
    #         raise Http404("Not a valid number for page.")

    #     if page_no < 1:
    #         raise Http404("Pages should be 1 or greater.")

    #     start_offset = (page_no - 1) * self.results_per_page
    #     self.results[start_offset : start_offset + self.results_per_page]

    #     paginator = Paginator(self.results, self.results_per_page)

    #     try:
    #         page = paginator.page(page_no)
    #     except InvalidPage:
    #         raise Http404("No such page!")

    #     return (paginator, page)

    # def extra_context(self):
    #     """
    #     Allows the addition of more context variables as needed.

    #     Must return a dictionary.
    #     """
    #     return {}

    # def get_context(self):
    #     (paginator, page) = self.build_page()

    #     context = {
    #         "query": self.query,
    #         "form": self.form,
    #         "page": page,
    #         "paginator": paginator,
    #         "suggestion": None,
    #     }

    #     if (
    #         hasattr(self.results, "query")
    #         and self.results.query.backend.include_spelling
    #     ):
    #         context["suggestion"] = self.form.get_suggestion()

    #     context.update(self.extra_context())

    #     return context

    # def create_response(self):
    #     """
    #     Generates the actual HttpResponse to send back to the user.
    #     """

    #     context = self.get_context()

    #     return render(self.request, self.template, context)
