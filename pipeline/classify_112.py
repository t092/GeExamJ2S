#!/usr/bin/env python3
import json
import os

mapping = {
    # 歷史科
    6: {"subject": "歷史", "focus": "歷 A：臺灣的歷史", "content": "戒嚴時期雜誌社人員平反（《自由中國》、《美麗島》）"},
    8: {"subject": "歷史", "focus": "歷 A：臺灣的歷史", "content": "鄭氏政權與清朝、傳教士李科羅的往來"},
    17: {"subject": "歷史", "focus": "歷 A：臺灣的歷史", "content": "清末淡水、大稻埕的開港通商與茶葉貿易"},
    19: {"subject": "歷史", "focus": "歷 A：臺灣的歷史", "content": "日治時期霞喀羅警備道路與理蕃政策"},
    38: {"subject": "歷史", "focus": "歷 A：臺灣的歷史", "content": "臺灣歷史小說順序（抗日、文化協會、南洋戰場）"},
    
    5: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "清末婦女自幼纏足的風俗廢除"},
    20: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "西安事變（蔣中正與張學良）的政治主張"},
    30: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "中共改革開放與設立經濟特區"},
    32: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "西周封建制度與身分等級"},
    39: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "1830 年代清朝生絲出口廣州的情況"},
    44: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "琉球王國與中國的朝貢關係"},
    45: {"subject": "歷史", "focus": "歷 B：中國與東亞的歷史", "content": "日本藉牡丹社事件擴張並併吞琉球"},
    
    7: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "法國 18-20 世紀因戰爭導致的平均壽命變動"},
    18: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "盧梭《社會契約論》與主權在民理念"},
    29: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "古埃及依據尼羅河氾濫制定的太陽曆法"},
    31: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "俄國因共產政權成立退出一戰、二戰德國投降"},
    33: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "查理曼時期的文化復興與基督教教士的角色"},
    41: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "印度莫臥兒帝國（伊斯蘭與波斯風格）建築"},
    50: {"subject": "歷史", "focus": "歷 C：世界的歷史", "content": "開普敦奴隸來自荷蘭在亞洲（南洋群島）的殖民地"},

    # 地理科
    2: {"subject": "地理", "focus": "地 A：臺灣與在地環境", "content": "臺灣「幸福巴士」營運行政區的分布"},
    28: {"subject": "地理", "focus": "地 A：臺灣與在地環境", "content": "臺灣氣象測站經緯度與降水量判斷"},
    34: {"subject": "地理", "focus": "地 A：臺灣與在地環境", "content": "臺灣不同地區醫療資源分佈數據分析"},
    37: {"subject": "地理", "focus": "地 A：臺灣與在地環境", "content": "臺灣少子女化與社會增加（歸化入籍）對策"},
    
    4: {"subject": "地理", "focus": "地 B：中國與東亞（含區域地理）", "content": "中國人口普查幼年比例與開放二胎政策"},
    14: {"subject": "地理", "focus": "地 B：中國與東亞（含區域地理）", "content": "湖北襄陽水位變化與季節性降水關係"},
    46: {"subject": "地理", "focus": "地 B：中國與東亞（含區域地理）", "content": "富士山登山季節與積雪融化"},
    47: {"subject": "地理", "focus": "地 B：中國與東亞（含區域地理）", "content": "富士山登山路線等高線圖判斷"},
    48: {"subject": "地理", "focus": "地 B：中國與東亞（含區域地理）", "content": "富士山登山路線平均坡度計算"},
    
    3: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "格陵蘭全球暖化對當地生活（冰層變薄）的影響"},
    13: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "熱帶乾燥地區椰棗分布（北非地區）"},
    15: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "CPTPP 成員國與廢除關稅的貿易衝擊"},
    16: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "波里尼西亞與毛利文化的地理位置判斷"},
    21: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "雅加達遷都婆羅洲的機會成本與生態考量"},
    26: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "泛美公路與巴拿馬至哥倫比亞段的熱帶雨林保護"},
    27: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "西班牙火山噴發熔岩流向與風向關係"},
    49: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "開普敦的地中海型氣候特色（一月溫暖雨少）"},
    51: {"subject": "地理", "focus": "地 C：全球環境與世界體系", "content": "蘇伊士運河開通大幅縮短前往印度洋的航程"},

    # 公民與社會科
    12: {"subject": "公民", "focus": "公 A：社會互動與文化", "content": "太魯閣族祭儀假期的法律依據與多元文化傳承"},
    43: {"subject": "公民", "focus": "公 A：社會互動與文化", "content": "女性勞動參與原因調查與家庭平權觀念"},
    53: {"subject": "公民", "focus": "公 A：社會互動與文化", "content": "反體罰宣傳標語與改變家長價值觀的社會變遷"},
    
    1: {"subject": "公民", "focus": "公 B：市場與經濟", "content": "開發新米食以減輕稻米過剩壓力"},
    23: {"subject": "公民", "focus": "公 B：市場與經濟", "content": "臺灣家庭可支配所得成長率與貧富差距現象"},
    35: {"subject": "公民", "focus": "公 B：市場與經濟", "content": "飢餓行銷對消費欲望的非金錢誘因影響"},
    40: {"subject": "公民", "focus": "公 B：市場與經濟", "content": "匯率變動對甲乙兩國進出口銷售量與價格的影響"},
    
    9: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "外籍人士接種疫苗權益與基本人權保障"},
    10: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "國家領土組成範圍（領土、領海、領空）判定"},
    11: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "校園惡作劇致人受傷之民事損害賠償"},
    24: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "立法委員對衛福部長的質詢與預算審查權"},
    36: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "幽靈人口遷移戶籍意圖影響選舉之刑事責任"},
    42: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "供應不實有機農產品之行政罰鍰處分"},
    54: {"subject": "公民", "focus": "公 C：權力、社會與法律", "content": "法律修訂程序（經總統公布後生效）"},
    
    22: {"subject": "公民", "focus": "公 D：全球連結與地球村", "content": "一個中國原則對我國參與國際刑警組織（治安風險）之影響"},
    25: {"subject": "公民", "focus": "公 D：全球連結與地球村", "content": "世界銀行經濟實力示意圖與各國 GDP 規模"},
    52: {"subject": "公民", "focus": "公 D：全球連結與地球村", "content": "國際活動理念（反體罰）在全球化下的文化交流"}
}

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(project_root, "data", "112.json")
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    print(f"Loaded {len(questions)} questions from {json_path}.")
    
    updated_count = 0
    for q in questions:
        qnum = q.get("number")
        if qnum in mapping:
            info = mapping[qnum]
            q["subject"] = info["subject"]
            q["learning_focuses"] = [info["focus"]]
            q["learning_contents"] = [info["content"]]
            updated_count += 1
        else:
            print(f"Warning: Question {qnum} not in mapping!")
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully classified {updated_count} questions in {json_path}.")

if __name__ == "__main__":
    main()
