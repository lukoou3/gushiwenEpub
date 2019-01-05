import shutil,os
from jinja2 import Environment, PackageLoader
import pymongo
from lxml import etree
import re
from itertools import zip_longest,groupby
import collections

def TestPrtPwd():
    print("获取当前文件路径——" + os.path.realpath(__file__))  # 获取当前文件路径
    parent = os.path.dirname(os.path.realpath(__file__))
    print("获取其父目录——" + parent)  # 从当前文件路径中获取目录
    garder = os.path.dirname(parent)
    print("获取父目录的父目录——" + garder)
    print("获取文件名" + os.path.basename(os.path.realpath(__file__)))  # 获取文件名
    # 当前文件的路径
    pwd = os.getcwd()
    print("当前运行文件路径" + pwd)
    # 当前文件的父路径
    father_path = os.path.abspath(os.path.dirname(pwd) + os.path.sep + ".")
    print("运行文件父路径" + father_path)
    # 当前文件的前两级目录
    grader_father = os.path.abspath(os.path.dirname(pwd) + os.path.sep + "..")
    print("运行文件父路径的父路径" + grader_father)
    return garder

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
    re_zhu = re.compile(r"<br/{0,1}>\s*<span.+",re.DOTALL)

    def __init__(self,*args, **kwargs):
        if os.path.exists(self.tmp_path):
            shutil.rmtree(self.tmp_path)
        shutil.copytree(self.base_path, self.tmp_path)
        super().__init__(*args, **kwargs)

    def handle_data(self,data):
        #data["yizhu_cont"] = None if not data.get("yizhu_cont") else data.get("yizhu_cont").replace("float:left;","")
        data["yizhu_zhu"] = None if not data.get("yizhu_zhu") else data.get("yizhu_zhu").replace("float:left;","")
        data["yizhu_yi"] = None if not data.get("yizhu_yi") else data.get("yizhu_yi").replace("float:left;", "")
        data["yizhu_shang"] = None if not data.get("yizhu_shang") else data.get("yizhu_shang").replace("float:left;", "")
        if data["yizhu_zhu"] or data["yizhu_yi"]:
            zhu_list = []
            html = etree.HTML(data["yizhu_zhu"] if data["yizhu_zhu"] else "<div></div>")
            html_yi = etree.HTML(data["yizhu_yi"] if data["yizhu_yi"] else "<div></div>")
            ps = html.xpath("//body/p[not(contains(@style,'color:#919090'))]")
            ps_yi = html_yi.xpath("//body/p[not(contains(@style,'color:#919090'))]")
            re_str = """<sup><a class="duokan-footnote" href="#{}" style="text-decoration: none!important"><img alt="" src="../Images/{}"/></a></sup>"""
            for i,(p,p_yi) in enumerate(zip_longest(ps,ps_yi,fillvalue=None)):
                if p_yi is not None:
                    html_p = etree.tostring(p, encoding="utf-8", pretty_print=False, method="html").decode()
                else:
                    html_p = None
                if p_yi is not None:
                    html_p_yi = etree.tostring(p_yi,encoding="utf-8", pretty_print=False, method="html").decode()
                else:
                    html_p_yi = None

                cont = zhu = yi = None
                zhu_imgs = []
                if html_p and self.re_zhu.search(html_p):
                    if not cont:
                        cont = self.re_zhu.sub("",html_p)
                    zhu = p.xpath("./span[@style='color:#286345;'][last()]/text()")[0]
                    zhu_imgs.append(re_str.format("A_zhu_{}_{}".format(data.get("_id",""),i),"note.png"))
                if html_p_yi and self.re_zhu.search(html_p_yi):
                    if not cont:
                        cont = self.re_zhu.sub("",html_p_yi)
                    yi = p_yi.xpath("./span[@style='color:#76621c;'][last()]/text()")[0]
                    zhu_imgs.append(re_str.format("A_yi_{}_{}".format(data.get("_id", ""), i),"note1.png"))
                if not cont:
                    cont = html_p or html_p_yi
                else:
                    cont = "{}{}</p>".format(cont,"".join(zhu_imgs))

                zhu_list.append({"cont":cont,"zhu":zhu,"yi":yi,
                                 "id_zhu":"A_zhu_{}_{}".format(data.get("_id",""),i),
                                 "id_yi": "A_yi_{}_{}".format(data.get("_id", ""), i)})
            data["zhu_list"] = zhu_list


    def create_epub(self):
        dynastys = ["先秦", "两汉", "魏晋", "南北朝", "隋代", "唐代", "五代", "宋代", "金朝", "元代", "明代", "清代","近代","现代","近现代"]
        dynasty_sort = {dynasty:i for i,dynasty in enumerate(dynastys,start=1)}

        client = pymongo.MongoClient(host='localhost', port=27017)
        db = client.gushiwen
        tb = db.gushiwen
        datas = [item for item in tb.find().sort("dynasty")]
        #datas = [item for item in tb.find({},{"_id": 0,"dynasty": 1,"author": 1,"title": 1}).sort("dynasty")]
        author_dict = {item.get("name"):item.get("info") for item in db.gushiwen_author.find()}

        dynasty_author_list = [(item.get("dynasty"),item.get("author")) for item in datas]
        dynasty_author_sort = collections.Counter(dynasty_author_list)

        datas.sort(key=lambda item: dynasty_sort.get(item.get("dynasty"),0))#需要先排序，然后才能groupby。lst排序后自身被改变
        datas_group = groupby(datas,key=lambda item:item.get("dynasty")) #返回迭代器生成元素(key, group)，其中key是分组的键值，group是迭代器，生成组成该组的所有项。
        datas_group = [(dynasty,sorted(group,
            key=lambda item: ( dynasty_author_sort.get( (item.get("dynasty"),item.get("author")) ) ,item.get("author"),int(item.get("good")) )
                        ,reverse=True)
                        )
                       for dynasty,group in datas_group]
        datas = []
        for dynasty,items in datas_group:
            items_group = groupby(items,key=lambda item:item.get("author"))
            author_group = [(author,list(group)) for author,group in items_group]
            datas.append( (dynasty,author_group) )

        """import pprint
        pprint.pprint(datas)
        client.close()
        return"""
        """for i,data in enumerate(datas,start=1):
            self.handle_data(data)
        client.close()
        return"""

        #shutil.copy(os.path.join(self.temp_path, "Text/bt-temp.html"),os.path.join(self.tmp_path, "OEBPS/Text/bt-temp.html"))
        env = Environment(loader=PackageLoader('pyepub', "epubtemp"))

        template_author = env.get_template('Text/at-temp.html')
        template_data = env.get_template('Text/bt-temp.html')
        for i,(dynasty,dynasty_datas) in enumerate(datas,start=1):
            for j,(author,author_datas) in enumerate(dynasty_datas,start=1):
                #template_author = env.get_template('Text/at-temp.html')
                content = template_author.render(name=author,info=author_dict.get(author))
                file_name = "bt-{}-{}.html".format(i,j)
                with open(os.path.join(self.tmp_path, "OEBPS/Text/{}".format(file_name)), "w", encoding="utf-8") as fp:
                    fp.write(content)
                    manifest.append({"href": "Text/{}".format(file_name), "id": file_name,
                                     "media-type": "application/xhtml+xml"})

                for k,data in enumerate(author_datas,start=1):
                    self.handle_data(data)
                    #template_data = env.get_template('Text/bt-temp.html')
                    content = template_data.render(title=data.get("title"),tags="，".join(data.get("tags",[])),
                        dynasty=data.get("dynasty"),author=data.get("author"),
                        beijings=data.get("beijings",[]),
                        yizhu_cont=data.get("yizhu_cont"), yizhu_yi=data.get("yizhu_yi"),
                                yizhu_zhu=data.get("yizhu_zhu"),yizhu_shang=data.get("yizhu_shang"),
                                zhu_list=data.get("zhu_list",[]))
                    file_name = "bt-{}-{}-{}.html".format(i,j,k)
                    with open(os.path.join(self.tmp_path, "OEBPS/Text/{}".format(file_name)), "w", encoding="utf-8") as fp:
                        fp.write(content)
                        manifest.append({"href":"Text/{}".format(file_name),"id":file_name,
                                         "media-type":"application/xhtml+xml"})

        manifest.append({"href":"Text/result.html","id":"result.html",
                                 "title":"结束","media-type":"application/xhtml+xml"})
        spine = [{"idref": item["id"]} for item in manifest]

        template = env.get_template('content.opf')
        content = template.render(metadata=metadata, manifest=manifest, spine=spine)
        with open(os.path.join(self.tmp_path, "OEBPS/content.opf"), "w", encoding="utf-8") as fp:
            fp.write(content)


        navPoints = []
        navPoints.append(NavPoint("封面", "Text/cover.html"))
        for i, (dynasty, dynasty_datas) in enumerate(datas, start=1):
            navPoint_author_list = []
            for j, (author, author_datas) in enumerate(dynasty_datas, start=1):
                navPoint_author = NavPoint(author, "Text/bt-{}-{}.html".format(i,j) ,
                         [NavPoint(data["title"],"Text/bt-{}-{}-{}.html".format(i,j,k))  for k, data in enumerate(author_datas,start=1)])
                navPoint_author_list.append(navPoint_author)
            navPoint_dynasty = NavPoint(dynasty, navPoint_author_list[0].src,navPoint_author_list)
            navPoints.append(navPoint_dynasty)
        navPoints_order(navPoints)

        template = env.get_template('toc.ncx')
        content = template.render(title="古诗文", navPoints=navPoints)
        with open(os.path.join(self.tmp_path, "OEBPS/toc.ncx"),"w",encoding="utf-8") as fp:
            fp.write(content)
        """
        with zipfile.ZipFile("gushiwen.epub", "w", zipfile.ZIP_DEFLATED) as epub:
            for current_path, subfolders, filesname in os.walk(self.tmp_path):
                print(current_path, subfolders, filesname)
                #  filesname是一个列表，我们需要里面的每个文件名和当前路径组合
                for file in filesname:
                    # 将当前路径与当前路径下的文件名组合，就是当前文件的绝对路径
                    epub.write(os.path.join(current_path, file))
        """
        shutil.make_archive("gushiwen","zip", self.tmp_path)
        shutil.move("gushiwen.zip", "gushiwen.epub")

        client.close()

EpubBook().create_epub()