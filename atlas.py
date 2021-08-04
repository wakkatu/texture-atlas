import argparse
import itertools
import pprint
import sys
import weakref

class _PrettyPrinter(pprint.PrettyPrinter, object):
    def _format(self, obj, *args, **kwargs):
        if hasattr(obj, 'pformat_obj'):
            obj = obj.pformat_obj()
        super(_PrettyPrinter, self)._format(obj, *args, **kwargs)

pprint.PrettyPrinter = _PrettyPrinter
pprint = pprint.pprint

class Dataset(object):
    keys = ()
    def __init__(self, **kwargs):
        for k in self.keys:
            setattr(self, k, None)
        for k, v in kwargs.items():
            if k not in self.keys:
                raise TypeError(
                    "__init__() got an unexpected keyword argument '%s'" % k
                )
            setattr(self, k, v)
    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(
                "%s=%r" % (k, getattr(self, k))
                    for k in self.keys if getattr(self, k) is not None
            ),
        )
    def pformat_obj(self):
        return {
            k: getattr(self, k) \
                for k in self.keys if getattr(self, k) is not None
        }

class Page(Dataset):
    keys = (
        'name',
        'format',
        'min_filter',
        'mag_filter',
        'width',
        'height',
        'repeat',
    )
    def __init__(self, **kwargs):
        super(Page, self).__init__(**kwargs)

class Region(Dataset):
    keys = (
        'page',
        'name',
        'rotate',
        'x',
        'y',
        'width',
        'height',
        'orig_width',
        'orig_height',
        'offset_x',
        'offset_y',
        'index',
    )
    def __init__(self, page, **kwargs):
        if not isinstance(page, Page):
            raise TypeError("page is not Page")
        kwargs['page'] = weakref.ref(page)
        super(Region, self).__init__(**kwargs)

class Atlas(object):
    def __init__(self, regions=None):
        self.pages = []
        self.regions = weakref.WeakKeyDictionary()
        for region in regions or ():
            self.add_region(region)
    def __iter__(self):
        return itertools.chain(*(self.regions[page] for page in self.pages))
    def __repr__(self):
        return "%s(regions=%r)" % (
            self.__class__.__name__,
            list(self),
        )
    def pformat_obj(self):
        return {
            'pages': self.pages,
            'regions': list(self),
        }

    def add_region(self, region):
        page = region.page()
        if page is None:
            raise ValueError("page is None")
        if page not in self.regions:
            self.pages.append(page)
            self.regions[page] = []
        self.regions[page].append(region)

    @staticmethod
    def load_atlas(reader):
        atlas = Atlas()
        page = None
        region = None
        for line in reader:
            line = line.strip()
            if line == "":
                page = None
                region = None
            elif ':' in line:
                k, v = [x.strip() for x in line.split(':', 1)]
                if region is not None:
                    if k == 'rotate':
                        v = v != 'false'
                        setattr(region, k, v)
                    elif k == 'xy':
                        v = [int(x.strip()) for x in v.split(',', 1)]
                        setattr(region, 'x', v[0])
                        setattr(region, 'y', v[1])
                    elif k == 'size':
                        v = [int(x.strip()) for x in v.split(',', 1)]
                        setattr(region, 'width', v[0])
                        setattr(region, 'height', v[1])
                    elif k == 'orig':
                        v = [int(x.strip()) for x in v.split(',', 1)]
                        setattr(region, 'orig_width', v[0])
                        setattr(region, 'orig_height', v[1])
                    elif k == 'offset':
                        v = [int(x.strip()) for x in v.split(',', 1)]
                        setattr(region, 'offset_x', v[0])
                        setattr(region, 'offset_y', v[1])
                    elif k == 'index':
                        v = int(v)
                        setattr(region, k, v)
                    else:
                        setattr(page, k, v)
                elif page is not None:
                    if k == 'size':
                        v = [int(x.strip()) for x in v.split(',', 1)]
                        setattr(page, 'width', v[0])
                        setattr(page, 'height', v[1])
                    elif k == 'filter':
                        v = [x.strip() for x in v.split(',', 1)]
                        setattr(page, 'min_filter', v[0])
                        setattr(page, 'mag_filter', v[1])
                    else:
                        setattr(page, k, v)
            elif page is None:
                page = Page(name=line)
            else:
                region = Region(page, name=line)
                atlas.add_region(region)
        return atlas

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true')
    parser.add_argument('-f', '--infile', type=argparse.FileType('r'),
        default=sys.stdin)
    parser.add_argument('attr', nargs='*', metavar='ATTR')
    args = parser.parse_args()

    atlas = Atlas.load_atlas(args.infile)

    if args.interactive:
        if sys.stdout.isatty():
            from code import interact
            interact(local=globals())
            sys.exit()

    o = atlas
    for a in args.attr:
        if hasattr(o, a):
            o = getattr(o, a)
        elif a.isdigit():
            o = o[int(a)]
        else:
            o = o[a]
    pprint(o)
