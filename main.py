#coding: utf-8
import sqlite3
import pandas as pd
import re
import json
from workflow import Workflow3
import sys
import os
import plistlib


class ClipHist:
    def __init__(self, item, ts, app, appPath):
        self.item = item
        self.ts = ts
        self.app = app
        self.appPath = appPath

    def __repr__(self):
        return json.dumps(self.__dict__)


def get_clip_hist():
    limit = 500
    offset = 0
    while True:
        conn = sqlite3.connect(clipboard_db_fn)
        df = pd.read_sql_query(
            'select * from clipboard where dataType=0 order by ts desc limit {} offset {}'.format(limit, offset), conn)
        data = list(df.T.to_dict().values())
        if not data:
            return

        for i in data:
            yield ClipHist(i['item'], i['ts'], i['app'], i['apppath'])

        offset = offset + limit


def get_clipboard_fn():
    base_dn = os.path.dirname(os.path.dirname(wf.datadir))
    return os.path.join(base_dn, 'Databases', 'clipboard.alfdb')


def search_clip(input):
    try:
        pt = re.compile(re_fix(input))
        matched_item = set()
        rst = []
        # 两种匹配模式：正则和字符串in
        test_func = [
            lambda i: pt.match(i),
            lambda i: input in i
        ]
        for func in test_func:
            hist_generator = get_clip_hist()
            for i in hist_generator:
                if not func(i.item):
                    continue
                if i.item in matched_item:
                    continue
                rst.append(i)
                matched_item.add(i.item)

                if len(rst) > 9:
                    return rst

        return rst
    except Exception as e:
        return [ClipHist(str(e), 0, 'Exception', None)]


def re_fix(input):
    if input.endswith('$') and not input.startswith('.*?'):
        return '.*?' + input
    return input


def main(_):
    arg = u' '.join(wf.args).strip()
    rst = search_clip(arg)
    add_to_workflow(rst)
    wf.send_feedback()


def add_to_workflow(results):
    for itm in results:
        wf.add_item(
            title=itm.item,
            subtitle=itm.app,
            valid=True,
            icon=get_app_icon(itm.appPath),
            uid=itm.ts,
            arg=itm.item  # 传递给后面的节点
        )

    if not results:
        wf.add_item(
            title=u'没找到',
            valid=True,
        )


def get_app_icon(appPath):
    try:
        fn = os.path.join(appPath, 'Contents', 'Info.plist')
        obj = plistlib.readPlist(fn)
        icon_fn = obj.get('CFBundleIconFile')
        if not icon_fn:
            return
        if '.' not in icon_fn:
            icon_fn = icon_fn + '.icns'
        icon_dn = os.path.join(appPath, 'Contents', 'Resources')
        icon = os.path.join(icon_dn, icon_fn)
        if os.path.exists(icon):
            return icon
    except Exception as e:
        pass
    return os.path.join(os.getcwd(), 'icon.png')


if __name__ == "__main__":
    wf = Workflow3()
    clipboard_db_fn = get_clipboard_fn()
    sys.exit(wf.run(main))
