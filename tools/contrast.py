"""Measures contrast for every colour pair used by Stallboard concept C. Run: python3 tools/contrast.py"""
def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c: c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
L=dict(bg='#FFF4E2',surface='#FFFFFF',ink='#241438',muted='#54456B',line='#7A6A94',accent='#9C1B0D',onaccent='#FFFFFF',link='#9C1B0D',soft='#FFE3C2',focus='#241438',hero='#FFD23F',ok='#0F5C2E',okbg='#DDF3E4')
D=dict(bg='#1A1030',surface='#2A1D47',ink='#FFF1DC',muted='#D3C7E8',line='#9A8CB8',accent='#FFA37C',onaccent='#2A0C02',link='#FFA37C',soft='#3A2A63',focus='#FFF1DC',hero='#FFD23F',ok='#8FE0AA',okbg='#12351F')
CATL={'Apps you can add':('#FF9E3D','#241438'),'Jellyfin':('#6B3FD4','#FFFFFF'),'Network':('#0B7A75','#FFFFFF'),'System':('#8FD3F4','#241438'),'Accessibility':('#FF8FC0','#241438'),'Downloads':('#B7E04A','#241438'),'Home':('#C72F20','#FFFFFF'),'Appearance':('#FFD23F','#241438')}
CATD={'Apps you can add':('#A34A00','#FFFFFF'),'Jellyfin':('#5A32C2','#FFFFFF'),'Network':('#00695F','#FFFFFF'),'System':('#0B5C8A','#FFFFFF'),'Accessibility':('#A3235F','#FFFFFF'),'Downloads':('#4F6E00','#FFFFFF'),'Home':('#B3261E','#FFFFFF'),'Appearance':('#7A5C00','#FFFFFF')}
def pairs(T,CAT):
    P=[('Text on page','ink','bg',4.5),('Text on card','ink','surface',4.5),('Muted text on page','muted','bg',4.5),('Muted text on card','muted','surface',4.5),
       ('Link on page','link','bg',4.5),('Link on card','link','surface',4.5),('Primary button text','onaccent','accent',4.5),('Primary button on page (edge)','accent','bg',3),
       ('Control border on card','line','surface',3),('Control border on page','line','bg',3),('Focus ring on page','focus','bg',3),('Focus ring on card','focus','surface',3),('Text on soft panel','ink','soft',4.5),('Link on soft panel','link','soft',4.5),
       ('Reviewed chip text','ok','okbg',4.5)]
    out=[(n,T[a],T[b],cr(T[a],T[b]),m) for n,a,b,m in P]
    for k,(bg,fg) in CAT.items(): out.append((f'Category {k}: text on tile',fg,bg,cr(fg,bg),4.5))
    return out
if __name__=='__main__':
    bad=0
    for name,T,C in (('Light',L,CATL),('Dark',D,CATD)):
        print('##',name)
        for n,a,b,r,m in pairs(T,C):
            ok='pass' if r>=m else 'FAIL'; bad+=ok=='FAIL'
            print(f'| {n} | {a} on {b} | {r:.2f}:1 | {m}:1 | {ok} |')
    print('fails',bad)
