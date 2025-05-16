import re

def replace_keywords_with_links(html_content, replacements):
    for keyword, link_html in replacements:
        # href属性を抽出
        href_match = re.search(r'href="([^"]*)"', link_html)
        if href_match:
            href = href_match.group(1)
            
            # target属性を抽出（存在する場合）
            target_match = re.search(r'target="([^"]*)"', link_html)
            target_attr = f' target="{target_match.group(1)}"' if target_match else ''
            
            # 新しいリンクを作成
            new_link = f'<a href="{href}"{target_attr}>{keyword}</a>'
            
            # キーワードを新しいリンクで置換
            pattern = re.compile(re.escape(keyword))
            html_content = pattern.sub(new_link, html_content)
    
    return html_content
# HTMLコンテンツのサンプル
html_content = '''
<p>太神山でのテント泊体験レポート<br/><br/>梅雨明けの太神山でテント泊を楽しんできました。太神山は大津市にある標高637mの低山で、初心者でも挑戦しやすい山として知られています[1][4]。<br/><br/>準備段階では、軽量化を心がけつつ必要な装備を揃えました。テント、寝袋、マット、ヘッドライト、携帯コンロ、調理器具、食料、水、防寒着、雨具などが主な持ち物です。初めてのテント泊だったため、装備選びには特に気を使いました。<br/><br/>1日目は登山口から約3時間かけて山頂付近のキャンプサイトに到着しました。途中、鹿の鳴き声を聞くなど、自然を身近に感じられる瞬間がありました。キャンプサイトでは、テント設営後に簡単な夕食を作り、満天の星空を眺めながら他の参加者と交流を楽しみました。<br/><br/>2日目は朝日とともに起床し、朝食後にテントを片付けて下山しました。下山中に一時的に道に迷う場面もありましたが、無事に登山口まで戻ることができました。<br/><br/>この体験を通じて、準備の大切さと自然の中で過ごすことの素晴らしさを実感しました。鹿の鳴き声や満天の星空など、印象的な思い出がたくさんできました[4]。<br/><br/>太神山は湖南アルプスの一部で、近くには堂山もあります。この地域は手軽に楽しめる山岳エリアとして人気があり、今回のような短期のテント泊登山に適しています[1][5]。<br/><br/>テント泊登山は準備
'''

# 置換するキーワードとリンクのリスト
replacements = [
    ('テント泊', '<a href="http://hb.afl.rakuten.co.jp/hgc/1feccffa.7c7bccd7.1feccffb.111f7d7e/?pc=https%3A//product.rakuten.co.jp/product/-/9c996843f40d53fa6bbd8300d3f1b9b1/%3Frafcid%3Dwsc_i_ps_1056199525991339251&m=https%3A//product.rakuten.co.jp/m/product/-/9c996843f40d53fa6bbd8300d3f1b9b1/%3Frafcid%3Dwsc_i_ps_1056199525991339251" target="_blank">'),
    ('低山', '<a href="http://hb.afl.rakuten.co.jp/hgc/1feccffa.7c7bccd7.1feccffb.111f7d7e/?pc=https%3A//product.rakuten.co.jp/product/-/579326138af9cec99d3f13fc7d764936/%3Frafcid%3Dwsc_i_ps_1056199525991339251&m=https%3A//product.rakuten.co.jp/m/product/-/579326138af9cec99d3f13fc7d764936/%3Frafcid%3Dwsc_i_ps_1056199525991339251" target="_blank">'),
    ('キャンプサイト', '<a href="http://hb.afl.rakuten.co.jp/hgc/1feccffa.7c7bccd7.1feccffb.111f7d7e/?pc=https%3A//product.rakuten.co.jp/product/-/2b3c3133d9a615d1a7a451e88df7d9c0/%3Frafcid%3Dwsc_i_ps_1056199525991339251&m=https%3A//product.rakuten.co.jp/m/product/-/2b3c3133d9a615d1a7a451e88df7d9c0/%3Frafcid%3Dwsc_i_ps_1056199525991339251" target="_blank">'),
    ('自然', '<a href="http://hb.afl.rakuten.co.jp/hgc/1feccffa.7c7bccd7.1feccffb.111f7d7e/?pc=https%3A//product.rakuten.co.jp/product/-/00a869433b08c4cfb802db4572cfe758/%3Frafcid%3Dwsc_i_ps_1056199525991339251&m=https%3A//product.rakuten.co.jp/m/product/-/00a869433b08c4cfb802db4572cfe758/%3Frafcid%3Dwsc_i_ps_1056199525991339251" target="_blank">')
]

# HTMLコンテンツにリンクを挿入
linked_content = replace_keywords_with_links(html_content, replacements)
print(linked_content)