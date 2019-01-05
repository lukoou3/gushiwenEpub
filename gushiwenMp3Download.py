# coding=utf-8
import os
import sys
import asyncio
import aiohttp
import aiofiles
import progressbar
import pymongo

def handle_down_name(name):
    return  name.replace("\"", "").replace("'", "").replace("/", "").replace(":", "").replace("*", "").replace("?", "").replace("<", "").replace(">", "").replace("|", "")

def downloadImgs(datalist, basepath="D:\pycharmWork\gushiwenEpub\mp3"):
    async def download_one(semaphore,session,url,name,path):
        path = os.path.join(basepath,path)
        if not os.path.exists(path):
            os.makedirs(path)
        path = os.path.join(path,name)
        if os.path.exists(path):  # 图片已存在,如果链接对应的图片已存在，则忽略下载
            return {'ignored': True  # 用于告知download_one()的调用方，此图片被忽略下载
            }

        try:
            async with semaphore:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_content = await response.read()  # Binary Response Content: access the response body as bytes, for non-text requests
                    else:
                        raise aiohttp.ClientError()
        except Exception as e:
            print(url)
            return {
                'failed': True  # 用于告知download_one()的调用方，请求此图片URL时失败了
            }

        async with aiofiles.open(path, 'wb') as f:
            await f.write(image_content)
        return {
            'failed': False  # 用于告知download_one()的调用方，此图片被成功下载
        }

    async def download_many(datalist):
        async def download_buffer():
            nonlocal ignored_images,failed_images,visited_images
            to_do_iter = asyncio.as_completed(do_list)
            for i, future in enumerate(to_do_iter):
                result = await future
                if result.get('ignored'):
                    ignored_images += 1
                else:
                    if result.get('failed'):
                        failed_images += 1
                    else:
                        visited_images += 1
                bar.update(i if count <10000 else (count - 100000 + i) )
            do_list.clear()

        async with aiohttp.ClientSession() as session:  # aiohttp建议整个应用只创建一个session，不能为每个请求创建一个seesion
            semaphore = asyncio.Semaphore(900)  # 用于限制并发请求数量
            length = len(datalist)
            to_do = (download_one(semaphore, session,data["play_url"],handle_down_name(data["title"])+".mp3",data["author"])
                     for data in datalist)

            find_images = length  # 发现的总图片链接数
            ignored_images = 0  # 被忽略的图片数
            visited_images = 0  # 请求成功的图片数
            failed_images = 0  # 请求失败的图片数

            with progressbar.ProgressBar(max_value=find_images) as bar:
                count = 0
                do_list = []
                for do in to_do:
                    count += 1
                    do_list.append(do)
                    if(count %100000 == 0):
                        await download_buffer()
                if do_list:
                    await download_buffer()

        print('Find [{}] images, ignored [{}] images, visited [{}] images, failed [{}] images'.format(
            find_images, ignored_images, visited_images, failed_images))

    if sys.platform != 'win32':
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # syncio程序中的每个线程都有自己的事件循环，但它只会在主线程中为你自动创建一个事件循环
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_many(datalist))
    loop.close()

client = pymongo.MongoClient(host='localhost', port=27017)
db = client.gushiwen
tb = db.gushiwen
datas = [item for item in tb.find() if item.get("play_url")]
downloadImgs(datas, basepath="D:\pycharmWork\gushiwenEpub\mp3")
client.close()