#coding=utf8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import six.moves.cPickle as cPickle
import hashlib
import json
import os
import rdflib
import re
import tempfile


def ensure_unicode(s):
    return s if type(s) is type(u'') else s.decode('utf8')

def standard_dumps(obj):
    return obj


class RemoteApi:
    import requests

    def __init__(self, baseurl, apikey):
        self.baseurl = baseurl
        self.apikey = apikey

    def api_dialog(self, json_api, name):
        url = '{0}/{1}/{2}'.format(self.baseurl, name, self.apikey)
        headers = {'Content-Type': 'application/json'}
        response = self.requests.post(url=url, headers=headers, data=json.dumps(json_api).encode('utf-8'))
        return json.loads(response.text)

    def nlu(self, s):
        json_nlu = {'input': s}
        obj = self.api_dialog(json_nlu, name='nlu')
        patternlist = obj['msg']['patternlist']
        for i in range(len(patternlist)):
            patternlist[i]['_level'] = int(patternlist[i]['_level'])
            patternlist[i]['_matched_length'] = int(patternlist[i]['_matched_length'])
            for k, v in patternlist[i].items():
                if not k.startswith('_'):
                    sp = v.split(',')
                    if 1 != len(sp):
                        patternlist[i][k] = sp
        return standard_dumps(obj)

    def nlg(self, act_type, kw):
        json_nlg = {'_act_type': act_type}
        for k, v in kw.items():
            json_nlg[k] = v
        obj = self.api_dialog(json_nlg, name='nlg')
        return standard_dumps(obj)

    def kb(self, sparql):
        json_kb = {'sparql': sparql}
        obj = self.api_dialog(json_kb, name='kb')
        return standard_dumps(obj)


class Api:
    def __init__(self, rootdir):
        dicts = os.path.join(rootdir, 'dict')
        nlufile = os.path.join(rootdir, 'nlu.txt')
        nlgfile = os.path.join(rootdir, 'nlg.txt')
        kbfile = os.path.join(rootdir, 'kb.xml')
        self.keywords = {}
        self.patterns = []
        self.templates = []
        for filename in sorted(os.listdir(dicts)):
            with codecs.open(os.path.join(dicts, filename), 'r', 'utf8') as f:
                v = [line.strip() for line in f]
                v.sort(key=lambda s: (-len(s), s))
                p = re.compile('|'.join(v))
                self.keywords[filename] = (v, p)
        with codecs.open(nlufile, 'r', 'utf8') as f:
            for line in f:
                v = line.strip().split('\t')
                if len(v) <= 1:
                    continue
                pattern, action = v[:2]
                level = int(v[2]) if len(v) > 2 else 0
                now = [0]
                kw_table = {}
                r = re.compile('|'.join([re.escape(s) for s in self.keywords.keys()]))
                def g(m):
                    kw = m.group(0)
                    nowtext = '__{0}_'.format(now[0])
                    kw_table[nowtext] = kw
                    now[0] += 1
                    return '(?P<{0}>{1})'.format(nowtext, '|'.join(self.keywords[kw][0]))
                replaced = r.sub(g, pattern)
                self.patterns.append([re.compile(replaced), pattern, action, level, kw_table])
        with codecs.open(nlgfile, 'r', 'utf8') as f:
            bracket = re.compile('<([^>]+)>')
            for line in f:
                v = line.strip().split('\t')
                if len(v) <= 1:
                    continue
                act_type, pattern = v[:2]
                required_keys = []
                for m in bracket.finditer(pattern):
                    k = m.group(1)
                    if k not in required_keys:
                        required_keys.append(k)
                self.templates.append((act_type, pattern, sorted(required_keys)))
        with open(kbfile, 'rb') as f:
            kbcontent = f.read()
        kbsha256 = hashlib.sha256(kbcontent).hexdigest()
        kbpicklefile = os.path.join(rootdir, 'kb-{0}.pkl'.format(kbsha256))
        if os.path.exists(kbpicklefile):
            with open(kbpicklefile, 'rb') as f:
                self.graph = cPickle.load(f)
        else:
            print('converting {0} to {1}'.format(kbfile, kbpicklefile))
            self.graph = rdflib.Graph()
            self.graph.load(kbfile)
            with open(kbpicklefile, 'wb') as f:
                cPickle.dump(self.graph, f, protocol=2)

    def nlu(self, s):
        s = ensure_unicode(s)
        patternlist = list()
        for t in self.patterns:
            pattern = t[0]
            m = pattern.search(s)
            if m is not None:
                kw_table = t[4]
                matched = {}
                groupdict = m.groupdict()
                for name, value in groupdict.items():
                    if value is None:
                        continue
                    keyword = kw_table[name] if name in kw_table else name
                    if keyword not in matched:
                        matched[keyword] = value
                    elif type(matched[keyword]) is list:
                        matched[keyword].append(value)
                    else:
                        matched[keyword] = [matched[keyword], value]
                line = t[1:]
                matched.update({'_act_type': line[1], '_level': line[2], '_pattern': line[0], '_matched_length': len(m.group(0))})
                patternlist.append(matched)
        patternlist.sort(key=lambda d: (-d['_level'], -d['_matched_length']))
        keywords = dict()
        for kw, value in self.keywords.items():
            p = value[1]
            all = p.findall(s)
            if 0 < len(all):
                keywords[kw] = all
        result = {'error': 0, 'msg': {'patternlist': patternlist, 'keywords': keywords}}
        return standard_dumps(result)

    def nlg(self, act_type, kw):
        kw = {ensure_unicode(k): ensure_unicode(v) for k, v in kw.items()}
        sorted_keys = sorted(kw.keys())
        r = re.compile('<({0})>'.format('|'.join([re.escape(s) for s in sorted_keys])))
        results = [{'output': r.sub(lambda m: kw[m.group(1)], t[1]), 'pattern': t[1]}
                for t in filter(lambda t: t[0] == act_type and t[2] == sorted_keys, self.templates)]
        result = {'error': 0, 'msg': results}
        return standard_dumps(result)

    def kb(self, sparql):
        try:
            qres = self.graph.query(sparql)
            result = {'errno': 0, 'msg': [{k: v.toPython() for k, v in row.asdict().items()} for row in qres]}
        except Exception as e:
            result = {'errno': 1, 'msg': ensure_unicode(e.__str__())}
        return standard_dumps(result)
