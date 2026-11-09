# zzk/query_process/nodes/node_rrf.py

from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger

class NodeRrf(NodeBase):
    """
    节点功能：Reciprocal Rank Fusion
    将多路召回的结果（向量、HyDE、Web）进行加权融合排序。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_rrf"

    def process(self, state: QueryGraphState):
        embedding_chunks = state.get("embedding_chunks")
        hyde_embedding_chunks = state.get("hyde_embedding_chunks")

        #设定权重值 就是分子可以自己设定
        weighted_embedding_chunks = [
            (embedding_chunks,1),
            (hyde_embedding_chunks,1)
        ]


        # 我们的目的是想把两个列表当中的chunk放到一个容器里面
        # 如果有相同的，那么这个容器当中放一个就可以
        # 每个chunk都要有自己的排名分数，相同的chunk分数要加起来

        rrf_dict = {} #以chunk的id为键，以整个chunk为值

        for chunks,weight in weighted_embedding_chunks:
            for idx,chunk in enumerate(chunks,start=1):
                score = weight / (60 + idx)
                id = chunk.get("id")
                if id in rrf_dict:
                    # 有重复
                    rrf_dict[id]["score"] += score
                else:
                    # 没有重复
                    chunk["score"] = score  #把自己rrf算法算出来的排名分数替换掉向量检索出来的分数
                    rrf_dict[id] = chunk

        return {
            "rrf_chunks":sorted(rrf_dict.values(),key=lambda x: x["score"],reverse=True)[:10]
        }


    # 切分完成后做主体识别：根据 chunks 归纳出这份文档的知识主体（文件名不一定包含主题），
    # 即使暂时不考虑意图识别和 chunk 检索，也能增加 chunk 的语义标签。


    # 意图识别：根据用户问题和历史记录，让大模型识别用户要问的知识主体，
    # 再用识别结果去 item_name 表里做相似度检索，完成名称对齐。
    # 对齐之后按分数区分“确认的名字 / 可能的名字 / 噪音”，只有确认后才继续检索 chunk。


    # 向量检索和 HyDE 检索也会用到 item_name，此时它作为过滤条件：
    # 只有 chunk 的 item_name 命中本次确认的主体集合，才参与召回。














if __name__ == '__main__':
    node = NodeRrf()
    init_state = {
        "embedding_chunks":[
        {
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432459,
            "title": "## HAK 180 烫金机",
            "file_title": "hak180产品安全手册",
            "content": "## HAK 180 烫金机\n\n产品安全手册（简体中文）\n\n感谢您购买 HAK 180 烫金机。\n\n在使用本设备之前，请先阅读本手册，包括所有预防措施。阅读本手册后，请妥善保管。\n\n有关使用本设备的更多信息，请参阅使用说明书，其可在兄弟 (中国)商业有限公司技术服务支持网站 http://www.95105369.com/Web/Manuals.aspx 上找到。建议您先通读使用说明书，再使用本设备。\n\n如需获得常见问题解答、故障排除和说明书，请访问\n\nhttp://www.95105369.com。\n\n对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。",
            "score": 0.7724524736404419,
            "source": "local"
        },
        {
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432460,
            "title": "## HAK 180 烫金机",
            "file_title": "hak180产品安全手册",
            "content": "## HAK 180 烫金机\n\n对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。\n\n•\t对于保养、调整或维修事宜，请联系 Brother 呼叫中心或您当地的Brother 经销商。\n\n•\t如果本设备工作不正常或发生任何错误，请关闭本设备，拔下所有电缆，然后联系 Brother 呼叫中心或您当地的 Brother 经销商。\n\n•\t本文档中提供的信息可能会随时更改，恕不另行通知。\n\n•\t严禁未经授权擅自复制或重制本文档的任何部分或全部内容。",
            "score": 0.7701514959335327,
            "source": "local"
        },
        {
            "part": 7,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432469,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n![图片警示打印机内部高温部件（170°C/338°F）勿触碰，图示禁止手触灰色区域，并强调冷却后再操作，以防烫伤。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/37eecd8ac02745dac415a628b51c26974067062c9b9747c069579fdaa99dbae9.jpg)  \n儎⑟ഴḽ䆜઀ᛞ࠽व䀜᪮儎⑟Ⲻ䇴༽䜞ԬȾ",
            "score": 0.761888861656189,
            "source": "local"
        },
        {
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432464,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n•\t请勿拆解本设备。拆解本设备可能会导致火灾或触电。\n\n•\t请勿尝试自行维修本设备。打开或拆下盖子可能使您接触到危险电压点以及带来其他风险，并且可能使您的保修失效。对于所有维修事宜，请联系 Brother 呼叫中心或您当地的 Brother 经销商。\n\n•\t请在以下环境使用本设备：温度保持在 10 °C 和 32 °C 之间，湿度保持在 20% 和 80% 之间，无冷凝。\n\n•\t请勿使本设备受到阳光直射、过热、接触明火、腐蚀性气体、湿气或灰尘。否则可能产生触电、短路或火灾的风险，从而导致损坏设备和/ 或导致设备无法运行。\n\n•\t请勿将设备放在加热器、空调、电风扇或水附近。",
            "score": 0.7614810466766357,
            "source": "local"
        },
        {
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432463,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n•\t请先阅读这本手册，再尝试操作本设备或尝试进行任何维护。不按照这些说明操作可能会提高发生人员受伤或财产损坏（包括火灾、触电、烧伤或窒息所致）的风险。对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。\n\n•\t请勿在未去除所有包装材料的情况下使用本设备，包括本设备内部的任何附加的包装材料。否则可能会产生火灾的风险。\n\n•\t请勿拆解本设备。拆解本设备可能会导致火灾或触电。",
            "score": 0.7578579783439636,
            "source": "local"
        },
        {
            "part": 0,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432458,
            "title": "无标题",
            "file_title": "hak180产品安全手册",
            "content": "![图片为HAK 180烫金机产品安全手册封面，含条形码、型号D01WD7001-00及SCHN标识，提示用户阅读手册并访问指定网站获取说明书与支持。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/f93ddcd837fa399f0c165da43b0badb013c2961acc828a095c6d98f0a660dbca.jpg)  \nD01WD7001-00\n\nSCHN",
            "score": 0.7575223445892334,
            "source": "local"
        },
        {
            "part": 8,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432470,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n![图片展示一只手正在操作打开的设备内部（疑似打印机/复印机），结合文字提示，强调高温部件防烫伤、塑料袋窒息风险及电源安全注意事项。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/71f9e17a760882436455f7ddc3a5fd358ce821ceb6e598b76d013d93dc26c943.jpg)",
            "score": 0.7569114565849304,
            "source": "local"
        },
        {
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432475,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n![图片警示禁止将手伸入打印机进纸/出纸区域，以防被夹伤，强调操作时需避开图示危险部位。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/3bf3b3639360a2c43c223a6ee46c44b27d54f4a79506a17a8b99e6ba4703df40.jpg)",
            "score": 0.7551465630531311,
            "source": "local"
        },
        {
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432474,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "content": "## 设备\n\n•\t将本设备放置在平整、水平且稳定的表面上（如桌面），避免震动和冲击。\n\n•\t将本设备放置在通风良好的环境中。\n\n•\t为了防止人员受伤，请谨慎操作，避免将手指放置在图中所示的区域中。\n\n![图片警示勿将手指伸入设备内部纸张通道区域，以防夹伤；并展示电源插头清洁方法及安全操作要点。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/944ad0b1ae642d4a65bc1b40c979beeb12bc30e6a409b9d9666ee013ff48cc60.jpg)",
            "score": 0.5384927988052368,
            "source": "local"
        },
        {
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432478,
            "title": "## 为设备选择一个安全的位置",
            "file_title": "hak180产品安全手册",
            "content": "## 为设备选择一个安全的位置\n\n![图片对比展示了搬运设备的错误方式（抓托盘/出纸盒）与正确方式（双手托住设备底部），强调应避免部件脱落，确保安全搬运。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/0bc44b278a939f7ec6ff239a4423c46a74a6e07572150f9e912f5fa55e0f598d.jpg)",
            "score": 0.5250928401947021,
            "source": "local"
        }
    ],
        "hyde_embedding_chunks":[
        {
            "content": "## 设备\n\n•\t将本设备放置在平整、水平且稳定的表面上（如桌面），避免震动和冲击。\n\n•\t将本设备放置在通风良好的环境中。\n\n•\t为了防止人员受伤，请谨慎操作，避免将手指放置在图中所示的区域中。\n\n![图片警示勿将手指伸入设备内部纸张通道区域，以防夹伤；并展示电源插头清洁方法及安全操作要点。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/944ad0b1ae642d4a65bc1b40c979beeb12bc30e6a409b9d9666ee013ff48cc60.jpg)",
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432474,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8319130539894104,
            "source": "local"
        },
        {
            "content": "## 设备\n\n![图片展示一只手正在操作打开的设备内部（疑似打印机/复印机），结合文字提示，强调高温部件防烫伤、塑料袋窒息风险及电源安全注意事项。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/71f9e17a760882436455f7ddc3a5fd358ce821ceb6e598b76d013d93dc26c943.jpg)",
            "part": 8,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432470,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8304349184036255,
            "source": "local"
        },
        {
            "content": "## 设备\n\n![图片警示打印机内部高温部件（170°C/338°F）勿触碰，图示禁止手触灰色区域，并强调冷却后再操作，以防烫伤。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/37eecd8ac02745dac415a628b51c26974067062c9b9747c069579fdaa99dbae9.jpg)  \n儎⑟ഴḽ䆜઀ᛞ࠽व䀜᪮儎⑟Ⲻ䇴༽䜞ԬȾ",
            "part": 7,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432469,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8302913904190063,
            "source": "local"
        },
        {
            "content": "## 设备\n\n![图片警示禁止将手伸入打印机进纸/出纸区域，以防被夹伤，强调操作时需避开图示危险部位。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/3bf3b3639360a2c43c223a6ee46c44b27d54f4a79506a17a8b99e6ba4703df40.jpg)",
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432475,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8235640525817871,
            "source": "local"
        },
        {
            "content": "## HAK 180 烫金机\n\n对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。\n\n•\t对于保养、调整或维修事宜，请联系 Brother 呼叫中心或您当地的Brother 经销商。\n\n•\t如果本设备工作不正常或发生任何错误，请关闭本设备，拔下所有电缆，然后联系 Brother 呼叫中心或您当地的 Brother 经销商。\n\n•\t本文档中提供的信息可能会随时更改，恕不另行通知。\n\n•\t严禁未经授权擅自复制或重制本文档的任何部分或全部内容。",
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432460,
            "title": "## HAK 180 烫金机",
            "file_title": "hak180产品安全手册",
            "score": 0.8200991153717041,
            "source": "local"
        },
        {
            "content": "## 设备\n\n•\t请先阅读这本手册，再尝试操作本设备或尝试进行任何维护。不按照这些说明操作可能会提高发生人员受伤或财产损坏（包括火灾、触电、烧伤或窒息所致）的风险。对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。\n\n•\t请勿在未去除所有包装材料的情况下使用本设备，包括本设备内部的任何附加的包装材料。否则可能会产生火灾的风险。\n\n•\t请勿拆解本设备。拆解本设备可能会导致火灾或触电。",
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432463,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8097144961357117,
            "source": "local"
        },
        {
            "content": "## 设备\n\n如果遵守了操作说明进行操作，但是设备不能正确运行，请仅调整操作说明中涵盖的控制。错误调整其他控制可能导致损坏并且通常需要合格技术进行全面工作以将本设备恢复到正常操作。Brother不建议使用 Brother 正品烫金膜盒以外的其他品牌烫金膜盒。如果使用与本设备不兼容的耗材导致损坏本设备的任何零件，由此导致的任何维修可能不在保修范围内。",
            "part": 0,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432481,
            "title": "## 设备",
            "file_title": "hak180产品安全手册",
            "score": 0.8084437847137451,
            "source": "local"
        },
        {
            "content": "## HAK 180 烫金机\n\n产品安全手册（简体中文）\n\n感谢您购买 HAK 180 烫金机。\n\n在使用本设备之前，请先阅读本手册，包括所有预防措施。阅读本手册后，请妥善保管。\n\n有关使用本设备的更多信息，请参阅使用说明书，其可在兄弟 (中国)商业有限公司技术服务支持网站 http://www.95105369.com/Web/Manuals.aspx 上找到。建议您先通读使用说明书，再使用本设备。\n\n如需获得常见问题解答、故障排除和说明书，请访问\n\nhttp://www.95105369.com。\n\n对于本设备所有者不遵守本指南中规定的说明操作而导致的损害，Brother 不承担任何责任。",
            "part": 1,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432459,
            "title": "## HAK 180 烫金机",
            "file_title": "hak180产品安全手册",
            "score": 0.6413767337799072,
            "source": "local"
        },
        {
            "content": "![图片为HAK 180烫金机产品安全手册封面，含条形码、型号D01WD7001-00及SCHN标识，提示用户阅读手册并访问指定网站获取说明书与支持。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/f93ddcd837fa399f0c165da43b0badb013c2961acc828a095c6d98f0a660dbca.jpg)  \nD01WD7001-00\n\nSCHN",
            "part": 0,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432458,
            "title": "无标题",
            "file_title": "hak180产品安全手册",
            "score": 0.625781238079071,
            "source": "local"
        },
        {
            "content": "## 为设备选择一个安全的位置\n\n![图片对比展示了搬运设备的错误方式（抓托盘/出纸盒）与正确方式（双手托住设备底部），强调应避免部件脱落，确保安全搬运。](http://192.168.88.88:9000/knowledge-base/upload-images/20261017/hak180产品安全手册/0bc44b278a939f7ec6ff239a4423c46a74a6e07572150f9e912f5fa55e0f598d.jpg)",
            "part": 2,
            "item_name": "BrotherHAK180烫金机",
            "id": 469815669155432478,
            "title": "## 为设备选择一个安全的位置",
            "file_title": "hak180产品安全手册",
            "score": 0.6243244409561157,
            "source": "local"
        }
    ]
    }

    result = node(init_state)
    logger.info(json_format(result))
