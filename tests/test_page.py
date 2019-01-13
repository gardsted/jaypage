import unittest
from jaypage.page import Page
from urllib.parse import urlparse
import datetime
import collections

class Page(Page):
    @classmethod
    def get_fields_by_response(cls, response):
        try:
            loc_source = urlparse(response.url)
        except Exception as e:
            return {}
        if loc_source.netloc.endswith("ycombinator.com"):
            return {
                "text_keep" : ["css:tr.athing"],
                "link_keep" : [{'css:tr.athing': {"target":"css:a.storylink\href", "title":"css:a.storylink", "pubdate":"css:span.date"}}],
                "source_weight" : 42,
                "target_weight" : 42,
            }


class YcomResponse:
    url = "http://ycombinator.com"
    text = " ".join([
        "<html><body><tr class=\"athing\">Hello,",
        "<a class=\"storylink\" href=\"http://example.com\">",
        "Mulligan</a><span class=\"date\">First Date</span>",
        "<span class=\"date\">Second Date</span></tr></body></html>",
    ])

class Tests(unittest.TestCase):
    maxDiff = None

    def test_page_fall(self):
        p = Page.fromresponse(YcomResponse())
        self.assertEqual(p.fall(), 'body tr a span span')

    def test_page_init(self):
        p = Page(url="http://example.com", dom=None)
        self.assertEqual(p.fields, {
            'link_prune': ['xpath://style', 'xpath://script', 'xpath://comment()'],
            'link_keep': [{'xpath://a': {'target': 'css:a\href', 'title': 'css:a'}}],
            'loc_source': urlparse("http://example.com"),
            'source_weight': 1,
            'target_weight': 1,
            'text_keep': ['xpath://body'],
            'text_prune': ['xpath://style', 'xpath://script', 'xpath://comment()', 'css:script'],
            'linkitem': {}
        })

    def test_page_from_ycom_response(self):
        p = Page.fromresponse(YcomResponse())
        self.assertEqual(p.fields, {
            'link_prune': ['xpath://style', 'xpath://script', 'xpath://comment()'],
            "link_keep" : [{'css:tr.athing': {"target":"css:a.storylink\href", "title":"css:a.storylink", "pubdate":"css:span.date"}}],
            'loc_source': urlparse("http://ycombinator.com"),
            'source_weight': 42,
            'target_weight': 42,
            'text_keep': ['css:tr.athing'],
            'text_prune': ['xpath://style', 'xpath://script', 'xpath://comment()', 'css:script'],
            'linkitem': {},
        })


    def test_page_pageitem(self):
        p = Page.fromresponse(YcomResponse())
        p.now = datetime.datetime(2019,1,1,10,0,0)
        self.assertEqual({
            'id': '43f3e1132ca600be134f52eff3d7865d53646d28',
            'id.source': ['ff50c40c1ee184a2f5264d05618ae6c9ae813807'],
            'id.source.date': '43f3e1132ca600be134f52eff3d7865d53646d28',
            'source': collections.OrderedDict([
                ('scheme', 'http'),
                ('netloc', 'ycombinator.com'),
                ('path', ''),
                ('params', ''),
                ('query', ''),
                ('fragment', '')]),
            'text': ['Hello, Mulligan First Date Second Date'],
            'weight.source': 42,
            'when.date': datetime.date(2019, 1, 1),
            'when.retrieved': datetime.datetime(2019, 1, 1, 10, 0)
        }, p.pageitem)

    def test_page_linkitems(self):
        p = Page.fromresponse(YcomResponse())
        p.now = datetime.datetime(2019,1,1,10,0,0)
        self.assertEqual([{
            'id': '4c7a034e3d5a99eb549924687315c6f9b06deb16',
            'id.source': ['ff50c40c1ee184a2f5264d05618ae6c9ae813807'],
            'id.source.date': '43f3e1132ca600be134f52eff3d7865d53646d28',
            'id.source.target.date': '4c7a034e3d5a99eb549924687315c6f9b06deb16',
            'id.target': '47014b13456d9554edd0cf4567c07059ea1c7837',
            'pubdate': ['First Date', 'Second Date'],
            'source': collections.OrderedDict([
                ('scheme', 'http'),
                ('netloc', 'ycombinator.com'),
                ('path', ''),
                ('params', ''),
                ('query', ''),
                ('fragment', '')]),
            'target': collections.OrderedDict([
                ('scheme', 'http'),
                ('netloc', 'example.com'),
                ('path', ''),
                ('params', ''),
                ('query', ''),
                ('fragment', '')]),
            'weight.target': 42,
            'weight.source': 42,
            'title': ['Mulligan'],
            'when.date': datetime.date(2019, 1, 1),
            'when.retrieved': datetime.datetime(2019, 1, 1, 10, 0)}
        ], p.linkitems)

