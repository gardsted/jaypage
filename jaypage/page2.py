from lxml.html import fromstring, tostring
from urllib.parse import urlparse, urlunparse
import logging
import hashlib
import copy
import collections
import datetime
import asyncio
import chardet
import uuid

logger = logging.getLogger("page")

class Page():
    jobid = hashlib.sha1(str(datetime.datetime.now()).encode("utf-8")).hexdigest()

    def __init__(self, url, dom, **fields):
        """ fields are rules for extraction
        but also :
        * linkitem - transferring to page what was registered about the link
        ---
        each page/item is fitted with:
            source : urlparse of source url 
            target: urlparse of target url if any
            id.source (ids calculated  on source)
            id.target (ids calculated on target)
            id.job - what job is running this
            when.published - dates when page says it is published
            when.fetched - dates when page was fetched
            when.about - all dates on page
            who.author - who wrote it
            who.about - who is mentioned
            where.about - what countries/cities are mentioned
            what.about - what subjects/tags are covered
        """
        self.dom = dom
        self._text = None
        self._pageitem = None
        self._linkitems = None
        self._now = None
        self.fields = {
            "loc_source" : urlparse(url),
            "link_prune" : ["xpath://style","xpath://script","xpath://comment()"],
            "link_keep" : [{"xpath://a": {"target":"css:a\href","title":"css:a"}}],
            "text_prune" : ["xpath://style", "xpath://script", "xpath://comment()", "css:script"],
            "text_keep" : ["xpath://body"],
            "target_weight" : 1,
            "source_weight" : 1,
            "linkitem":{},
        }
        self.fields.update(fields)
        self._id = self.fields.get("linkitem",{}).get("id.target",None)


    @classmethod
    def fromresponse(cls, response, linkitem={}):
        try:
            fields = cls.get_fields_by_response(response)
            fields["linkitem"] = linkitem
            content = response.text
            dom = fromstring(content)
            dom.make_links_absolute(response.url)
            return cls(response.url, dom, **fields)
        except Exception as e:
            #logger.exception(e)
            return None

    @classmethod
    async def async_fromresponse(cls, response, linkitem={}):
        try:
            fields = cls.get_fields_by_response(response)
            fields["linkitem"] = linkitem
            content = await response.text()
            dom = fromstring(content, base_url = str(response.url))
            dom.make_links_absolute()
            return cls(str(response.url), dom, **fields)
        except Exception as e:
            #logger.exception(e)
            return None

    @classmethod
    def get(cls, *args, **kwargs):
        return requests.get(*args, **kwargs)

    @classmethod
    async def async_get(cls, session, *args, **kwargs):
        return session.get(*args, **kwargs)

    @classmethod
    def linktarget(cls, linkitem):
        return urlunparse([
            linkitem.get("target.scheme",[""])[0],
            linkitem.get("target.netloc",""),
            linkitem.get("target.path",""),
            linkitem.get("target.params",""),
            linkitem.get("target.query",""),
            linkitem.get("target.fragment",[""])[0]
        ])

    @classmethod
    def fromlinkitem(cls, linkitem):
        try:
            url = cls.linktarget(linkitem)
            response = cls.get(url)
            return cls.fromresponse(response, linkitem)
        except Exception as e:
            #logger.exception(e)
            return None

    @classmethod
    async def async_fromlinkitem(cls, session, linkitem):
        try:
            url = cls.linktarget(linkitem)
            response = await cls.async_get(session, url)
            return await cls.async_fromresponse(response, linkitem)
        except Exception as e:
            #logger.exception(e)
            return None

    @classmethod
    def domtree2text_fragments(cls, domtree):
        ' Returns all fragments of text contained in a subtree '
        r = []
        for e in domtree.getiterator(): # walks the subtree
            if e.text != None:
                r.append( " ".join([t for t in e.text.split()]))
            if e.tail != None:
                r.append( " ".join([t for t in e.tail.split()]))
        return " ".join([x.strip() for x in r if len(x.strip())])

    @classmethod
    def extract(cls, dom, keep_xpath=[], keep_css=[]):
        branches = []
        try:
            [branches.extend(dom.xpath(x)) for x in keep_xpath]
            [branches.extend(dom.cssselect(c)) for c in keep_css]
        except:
            logger.exception("css: %r, xpath: %r" %(keep_css, keep_xpath))
        return branches

    @classmethod
    def prune(cls, dom, prune_xpath=[], prune_css=[]):
        branches = []
        [branches.extend(dom.xpath(x)) for x in prune_xpath]
        [branches.extend(dom.cssselect(c)) for c in prune_css]
        for b in branches:
            try:
                b.drop_tree()
                del b
            except:
                pass

    @classmethod
    def get_fields_by_response(cls, response):
        raise NotImplementedError

    @classmethod
    def signature(cls, thing):
        return hashlib.sha1(repr(thing).encode("utf-8")).hexdigest()

    """ Text property,
        If You get it before setting it, it will be extracted from dom
    """
    def extracttext(self):
        dom = copy.deepcopy(self.dom)
        Page.prune(
            dom,
            prune_xpath = [x.split(":")[1] for x in self.fields["text_prune"] if x.startswith("xpath")],
            prune_css = [x.split(":")[1] for x in self.fields["text_prune"] if x.startswith("css")],
        )

        textparts = collections.OrderedDict()
        branches = Page.extract(
            dom,
            keep_xpath = [x.split(":")[1] for x in self.fields["text_keep"] if x.startswith("xpath")],
            keep_css = [x.split(":")[1] for x in self.fields["text_keep"] if x.startswith("css")],
        )
        texts = []
        [texts.append(Page.domtree2text_fragments(g)) for g in branches]
        [textparts.setdefault(t,1) for t in texts if len(t)]
        return list(textparts.keys())

    def gettext(self):
        if self._text == None:
            self.settext(self.extracttext())
        return self._text

    def settext(self, text):
        self._text = text

    text = property(gettext,settext)

    """ Id property,
        If You get it before setting it, it will be calculated
    """

    def getid(self):
        if self._id == None:
            self.setid(Page.signature((self.fields["loc_source"], self.now.date())))
        return self._id

    def setid(self, newid):
        self._id = newid

    id = property(getid,setid)

    """ Database item for saving in/retrieving Page from database
        If You get it before setting it, it will be calculated
    """

    def extractpageitem(self):
        id_source = [Page.signature(self.fields["loc_source"]._asdict())]
        extra_source_id = self.fields.get("target_id")
        if extra_source_id and not extra_source_id in id_source:
            id_source.append(extra_source_id)


        title, _title = "", self.dom.cssselect("head title")
        if len(_title):
            title = [t.text.strip() for t in _title]
        self._head = {
            "fb.title": title,
            "fb.description": " ".join(self.text[0:1])[:200],
            "fb.url": urlunparse(self.fields["loc_source"]),
        }

        for i in self.dom.cssselect("meta"):
            a = i.attrib
            if "content" in a:
                if "property" in a and ":" in a["property"]:
                    name = ".".join(a["property"].split(":"))
                    self._head.setdefault(name,[]).append(a["content"])
                if "name" in a and ":" in a["name"]:
                    name = ".".join(a["name"].split(":"))
                    self._head.setdefault(name,[]).append(a["content"])
        return {
            "id": self.id,
            "id.job" : self.jobid,
            "id.source.date": self.id,
            "id.source": id_source,
            "source": self.fields["loc_source"]._asdict(),
            "text": self.text,
            "when.date": self.now.date(),
            "when.retrieved": self.now,
            "weight.source": self.fields["source_weight"]
        }

    def getpageitem(self):
        if self._pageitem == None:
            self.setpageitem(self.extractpageitem())
        retval = dict(self._pageitem)
        retval.update(self._head)
        return retval

    def setpageitem(self, pageitem):
        self._pageitem = pageitem

    pageitem = property(getpageitem, setpageitem)


    """ Database item for saving in/retrieving Links from database
        If You get it before setting it, it will be calculated
    """

    def extractlinkitems(self):
        self.pageitem
        dom = copy.deepcopy(self.dom)
        items = []
        Page.prune(
            dom,
            prune_xpath = [x.split(":")[1] for x in self.fields["link_prune"] if x.startswith("xpath")],
            prune_css = [x.split(":")[1] for x in self.fields["link_prune"] if x.startswith("css")],
        )
        for link_keep in self.fields["link_keep"]:
            for pattern, fields in link_keep.items():
                _type, _pattern = pattern.split(":")
                if _type == "css":
                    branches = Page.extract(dom, keep_css=[_pattern])
                elif _type == "xpath":
                    branches = Page.extract(dom, keep_xpath=[_pattern])
                for branch in branches:
                    item = copy.copy(self._pageitem)
                    [item.pop(x,None) for x in ["text"]]
                    for field, pattern in fields.items():
                        _type, _pattern = pattern.split(":")
                        parts = _pattern.split("\\")
                        _attrib = False
                        if len(parts) == 2:
                            _pattern, _attrib = parts
                        elif len(parts) == 1:
                            pass
                        else:
                            raise ValueError("pattern must be type:path[\\attribute] - attribute is optional")
                        if _type == "css":
                            _branches = Page.extract(branch, keep_css=[_pattern])
                        elif _type == "xpath":
                            _branches = Page.extract(branch, keep_xpath=[_pattern])
                        if len(_branches) and _attrib:
                            item[field] = [x.attrib.get(_attrib) for x in _branches]
                        elif len(_branches):
                            item[field] = [Page.domtree2text_fragments(b) for b in _branches]
                    target = item.get("target")
                    if isinstance(target, list):
                        target = target[0]
                    if target == None:
                        target = ""
                    if not isinstance(target, str):
                        target = target.decode("ascii", "ignore")
                    item["target"] = urlparse(target)._asdict()
                    item["id.job"] = self.jobid
                    item["id"] = item["id.source.target.date"] = Page.signature(
                        (item["source"], item["target"], item["when.date"])
                    )
                    item["id.target"] = Page.signature(item["target"])
                    item["weight.target"] = self.fields["target_weight"]
                    items.append(item)
        return items

    def getlinkitems(self):
        if self._linkitems == None:
            self.setlinkitems(self.extractlinkitems())
        return self._linkitems

    def setlinkitems(self, linkitems):
        self._linkitems = linkitems

    linkitems = property(getlinkitems, setlinkitems)

    """ datetime is used to calculate ID's.
        It needs to be sattable for tests
    """
    def getnow(self):
        if self._now == None:
            self.setnow(datetime.datetime.utcnow())
        return self._now

    def setnow(self, now):
        self._now = now

    now = property(getnow, setnow)
