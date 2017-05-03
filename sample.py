#coding=utf8
import json
import api as localapi

def friendly_display(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=None, sort_keys=True))

def main():
    api = localapi.Api('config.sample')
    api2 = localapi.RemoteApi('http://115.182.62.171:9000/api', 'sg849KLWNETy6215zc9U1CapFlkt4JmC')

    query = '有什么不辣的川菜吗'
    friendly_display(api.nlu(query))
    friendly_display(api2.nlu(query))

    kw = {'name': '鱼香肉丝', 'taste': '甜'}
    friendly_display(api.nlg('answerNo', kw))
    friendly_display(api2.nlg('answerNo', kw))

    sparql = 'PREFIX r:<http://csaixyz.org/dish#> select ?o where { ?s r:has_taste "不辣"; r:dishtype "川菜"; r:name ?o. }'
    friendly_display(api.kb(sparql))
    friendly_display(api2.kb(sparql))

if __name__ == '__main__':
    main()
