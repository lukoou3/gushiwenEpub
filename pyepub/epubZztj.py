import shutil,os
from itertools import zip_longest
from jinja2 import Environment, PackageLoader
import pymongo
import re

class NavPoint():
    def __init__(self,text,src,childs=None,play_order=1):
        self.play_order = play_order
        self.text = text
        self.src = src
        self.childs = [] if childs is None else childs
    def add_childs(self,childs):
        for child in childs:
            self.childs.append(child)

def navPoints_order(navPoints):
    node_list = []
    index = 0
    for navPoint in navPoints:
        node_list.append(navPoint)
        while index < len(node_list):
            node = node_list[index]
            index = index + 1
            node.play_order = index
            node_list.extend(node.childs)

parent_path = os.path.dirname(os.path.realpath(__file__))

metadata = {"title":"古诗文","creator":"李奉超","publisher":"中国出版",
            "cover_jpg": "cover.jpg"}
manifest = []

class EpubBook():
    temp_path = os.path.join(parent_path,"epubtemp")
    base_path = os.path.join(parent_path, "epubbase")
    tmp_path = os.path.join(parent_path, "tmp")

    def __init__(self,*args, **kwargs):
        if os.path.exists(self.tmp_path):
            shutil.rmtree(self.tmp_path)
        shutil.copytree(self.base_path, self.tmp_path)
        super().__init__(*args, **kwargs)

    def handle_data(self, data):
        content = data["content"]
        content = re.sub(r"<a[^<>]+?show_key.[^<>]?>.*?</a>","",content)
        content = re.sub(r"""<font class="bj_style">.*?</font>""", "", content)
        if data["_id"] == 8:
            content = content.replace("于是就将冯去疾、李斯、冯劫交给*<br><br>", "")
        content = content.replace("*","<br>")
        datas = [data for data in content.split(r"<br>") if data.strip() != ""]
        datas[-1] = datas[-1][0:-6]
        print((len(datas),data["_id"]))
        #title = datas[0]
        """import pprint
        pprint.pprint(datas)"""
        contents = datas[1::2]
        annotations = datas[2::2]
        #content = "<br><br>".join(contents)

        zhu_list = []
        re_str = """<sup><a class="duokan-footnote" href="#{}" style="text-decoration: none!important"><img alt="" src="../Images/{}"/></a></sup>"""
        for i, (p, p_yi) in enumerate(zip_longest(contents, annotations, fillvalue=None)):
            cont = "<p>{}{}</p>".format(p, re_str.format("A_yi_{}".format(i),"note1.png"))
            zhu_list.append({"cont": cont, "yi": p_yi,
                             "id_yi": "A_yi_{}".format(i)})

        #data["content"] = content
        data["zhu_list"] = zhu_list


    def create_epub(self):
        client = pymongo.MongoClient(host='localhost', port=27017)
        db = client.gushiwen
        tb = db.zztj
        datas = [item for item in tb.find().sort("_id")]

        env = Environment(loader=PackageLoader('pyepub', "epubtemp"))
        template_data = env.get_template('Text/zztj-temp.html')

        for i,data in enumerate(datas,start=1):
            self.handle_data(data)
            content = template_data.render(zhu_list=data["zhu_list"])
            file_name = "bt-{}.html".format(i)
            with open(os.path.join(self.tmp_path, "OEBPS/Text/{}".format(file_name)), "w", encoding="utf-8") as fp:
                fp.write(content)
                manifest.append({"href": "Text/{}".format(file_name), "id": file_name,
                                 "media-type": "application/xhtml+xml"})
        return

        manifest.append({"href": "Text/result.html", "id": "result.html",
                         "title": "结束", "media-type": "application/xhtml+xml"})
        spine = [{"idref": item["id"]} for item in manifest]

        template = env.get_template('content.opf')
        content = template.render(metadata=metadata, manifest=manifest, spine=spine)
        with open(os.path.join(self.tmp_path, "OEBPS/content.opf"), "w", encoding="utf-8") as fp:
            fp.write(content)

        navPoints = []
        navPoints.append(NavPoint("封面", "Text/cover.html"))
        for i, data in enumerate(datas, start=1):
            navPoints.append(NavPoint(data["title"], "Text/bt-{}.html".format(i)))
        navPoints_order(navPoints)

        template = env.get_template('toc.ncx')
        content = template.render(title="资治通鉴", navPoints=navPoints)
        with open(os.path.join(self.tmp_path, "OEBPS/toc.ncx"), "w", encoding="utf-8") as fp:
            fp.write(content)
        shutil.make_archive("资治通鉴（注释版）", "zip", self.tmp_path)
        shutil.move("资治通鉴（注释版）.zip", "资治通鉴（注释版）.epub")

        client.close()

EpubBook().create_epub()