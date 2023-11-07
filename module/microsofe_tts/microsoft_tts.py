# -*- coding: utf-8 -*-
import json
import asyncio
import edge_tts

TEXT = "欢迎来到公众号思维兵工厂。生活就像海洋，只有意志坚强的人才能到达彼岸！"


async def download_voice(text, voice_choice, file_name) -> None:
    file_path = f"voice/{file_name}"
    communicate = edge_tts.Communicate(text, voice_choice)
    await communicate.save(file_path)
    print(voice_choice, file_path, 'finish')


async def handler():
    tasks = []

    with open('zh_.json', mode='r', encoding='utf8') as read_f:
        voice_data = json.load(read_f)

    for item in voice_data:
        gender = item['gender']
        name = item['name']
        nickname = item['nickname']
        sentence = item['sentence']

        if gender == 'Female':
            file_name = f"【女声】-{nickname}.mp3"
        else:
            file_name = f"【男声】-{nickname}.mp3"

        tasks.append(asyncio.create_task(download_voice(sentence, name, file_name)))

    await asyncio.wait(tasks)


def select_voice():
    with open('all_voice_info.json', mode='r', encoding='utf8') as read_f:
        voice_data = json.load(read_f)

    select_list = []
    for item in voice_data:
        language, location, name = item['name'].split('-', maxsplit=2)

        if language == 'zh':
            item['nickname'] = name.replace('Neural', '')
            item['language'] = language
            item['location'] = location
            item['sentence'] = '欢迎来到公众号思维兵工厂，我是你们的语音助手——'
            select_list.append(item)

    with open('zh_.json', mode='w', encoding='utf8') as write_f:
        write_f.write(json.dumps(select_list, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(handler())
# asyncio.run(download_voice('zh-HK-HiuMaanNeural', 'HiuMaan'))
