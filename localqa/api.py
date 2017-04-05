#coding=utf8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import json
import os
import re


def ensure_unicode(s):
    return s if type(s) == type(u'') else s.decode('utf8')

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
        print(dicts, nlufile, nlgfile)
        self.keywords = {}
        self.patterns = []
        self.templates = []
        for filename in os.listdir(dicts):
            with codecs.open(os.path.join(dicts, filename), 'r', 'utf8') as f:
                v = [line.strip() for line in f]
                self.keywords[filename] = v
        with codecs.open(nlufile, 'r', 'utf8') as f:
            for line in f:
                v = line.strip().split('\t')
                if len(v) <= 1:
                    continue
                pattern, action = v[:2]
                level = int(v[2]) if len(v) > 2 else 0
                replaced = pattern
                now = 0
                kw_table = {}
                for kw, value in self.keywords.items():
                    while True:
                        last_replaced = replaced
                        nowtext = 'p{0}'.format(now)
                        target = '(?P<{0}>{1})'.format(nowtext, '|'.join(value))
                        replaced = replaced.replace(kw, target, 1)
                        if replaced == last_replaced:
                            break
                        kw_table[nowtext] = kw
                        now += 1
                        if now >= 10:
                            raise ValueError('nlu too many keywords')
                self.patterns.append([re.compile(replaced), pattern, action, level, kw_table])
        with codecs.open(nlgfile, 'r', 'utf8') as f:
            bracket = re.compile('<(\w+)>')
            for line in f:
                v = line.strip().split('\t')
                if len(v) <= 1:
                    continue
                act_type, pattern = v[:2]
                required_keys = []
                for m in bracket.finditer(pattern):
                    k = m.group(1)
                    if k in required_keys:
                        raise ValueError('nlg keywords cannot appearance twice')
                    required_keys.append(k)
                self.templates.append((act_type, pattern, sorted(required_keys)))

    def nlu(self, s):
        s = ensure_unicode(s)
        results = list()
        for t in self.patterns:
            pattern = t[0]
            m = pattern.search(s)
            if m is not None:
                kw_table = t[4]
                matched = {}
                groupdict = m.groupdict()
                for name, value in groupdict.items():
                    keyword = kw_table[name]
                    if keyword not in matched:
                        matched[keyword] = value
                    elif list == type(matched[keyword]):
                        matched[keyword].append(value)
                    else:
                        matched[keyword] = [matched[keyword], value]
                results.append({'matches': matched, 'matched_length': len(m.group(0)), 'pattern': t[1:]})
        results.sort(key=lambda d: (-d['pattern'][2], -d['matched_length']))
        patternlist = list()
        for d in results:
            m = {'_act_type': d['pattern'][1], '_level': d['pattern'][2], '_pattern': d['pattern'][0],
                '_matched_length': d['matched_length']}
            for kw, value in d['matches'].items():
                m[kw] = value
            patternlist.append(m)
        result = {'error': 0, 'msg': {'patternlist': patternlist}}
        return standard_dumps(result)

    def nlg(self, act_type, kw):
        kw = {ensure_unicode(k): ensure_unicode(v) for k, v in kw.items()}
        sorted_keys = sorted(kw.keys())
        results = list()
        for t in self.templates:
            if t[0] == act_type and t[2] == sorted_keys:
                output = t[1]
                for k, v in kw.items():
                    output = output.replace('<{0}>'.format(k), v, 1)
                results.append({'output': output, 'pattern': t[1]})
        result = {'error': 0, 'msg': results}
        return standard_dumps(result)
