#coding=utf8
import json
import localqa


def friendly_display(obj):
    print json.dumps(obj, ensure_ascii=False, indent=None, sort_keys=True)

def main():
    api = localqa.api.Api('config.sample')
    api2 = localqa.api.RemoteApi('http://115.182.62.171:9000/api', 'jwqqetJagOHENburOW4I9LYcix2lxHZa')

    query = '你想要的是川菜还是青菜？'
    friendly_display(api.nlu(query))
    friendly_display(api2.nlu(query))

    kw = {'name': '鱼香肉丝', 'taste': '甜'}
    friendly_display(api.nlg('answerNo', kw))
    friendly_display(api2.nlg('answerNo', kw))
    
    sparql = 'PREFIX e:<http://csaixyz.org/dish/> PREFIX r:<http://csaixyz.org/dish#> select ?o where { ?s r:has_taste "不辣"; r:dishtype "川菜"; r:name ?o. }'
    friendly_display(api2.kb(sparql))

if __name__ == '__main__':
    main()
