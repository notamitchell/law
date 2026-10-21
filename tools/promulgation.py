"""Date and place of each law code, from the spreadsheet's free-text column.

The spreadsheet column "Place and date of promulgation" holds dates, places
and the scholars who propose them in one string, e.g.
"1018 (Whitelock, Kennedy, Wormald); Oxford". The clause pages show them as
separate lines:

    Date:  1018 (Whitelock, Kennedy, Wormald)
    Place: Oxford

TABLE gives, for every string the spreadsheet had in October 2026, its
dates and places, each with the scholars who propose it (an empty list
means the spreadsheet names nobody). Where a string is not in TABLE (the
spreadsheet has been changed), parse() splits it by rule: parts separated
by ";", a part with digits is a date, any other part a place, and names in
brackets at the end are its scholars. Check the page, and add the new
string to TABLE if the rule gets it wrong. See docs/OE-LAWS.md.
"""
import html
import re

W, WM, R, A, RB, K, L = 'Whitelock', 'Wormald', 'Robertson', 'Attenborough', 'Rabin', 'Kennedy', 'Liebermann'

# spreadsheet text -> ([(date, [scholars])], [(place, [scholars])])
TABLE = {
    '880–90; 886–90 (Whitelock)': ([('880–90', []), ('886–90', [W])], []),
    '601–4; 597–616, perhaps 602–3 (Whitelock)': ([('601–4', []), ('597–616, perhaps 602–3', [W])], []),
    '890–901; 885–899 (Whitelock)': ([('890–901', []), ('885–899', [W])], []),
    "925–40; before c.1110 (Nowell 'translation' from Q?)": ([('925–40', []), ('before c.1110 (Nowell’s ‘translation’ from Q?)', [])], []),
    '1002–23 (Whitelock); 1006–8 (Rabin)': ([('1002–23', [W]), ('1006–8', [RB])], []),
    'c.1020–c.1060; c.990–c.1020 (Wormald)': ([('c.1020–c.1060', []), ('c.990–c.1020', [WM])], []),
    "c.930–75; ?mid 990's (Wormald)": ([('c.930–75', []), ('?mid-990s', [WM])], []),
    '5 August 1100; Westminster (Robertson)': ([('5 August 1100', [])], [('Westminster', [R])]),
    '1018 (Whitelock, Kennedy, Wormald); Oxford': ([('1018', [W, K, WM])], [('Oxford', [])]),
    '1020; 1019/1020 (Robertson, Wormald); issued in England (Robertson).; end of 1019 or very beginning of 1020, probably written from Denmark (Whitelock)':
        ([('1020', []), ('1019/1020', [R, WM]), ('end of 1019 or very beginning of 1020', [W])],
         [('England', [R]), ('probably written from Denmark', [W])]),
    '1027; ?en route from Rome to Denmark (Robertson)': ([('1027', [])], [('?en route from Rome to Denmark', [R])]),
    'c.926–c.1000; c.930, ?Archenfield, on the Wye (Wormald)': ([('c.926–c.1000', []), ('c.930', [WM])], [('?Archenfield, on the Wye', [WM])]),
    'Nov. 921–938?; 1002–4 (Wormald, Rabin)': ([('Nov. 921–938?', []), ('1002–4', [WM, RB])], []),
    'c.1000–1050; ??(Whitelock); 1002x1008 (Rabin)': ([('c.1000–1050', []), ('1002×1008', [RB])], []),
    "c.900–c.1000, c. ?960; ?mid 990's (Wormald)": ([('c.900–c.1000, c. ?960', []), ('?mid-990s', [WM])], []),
    '960 (c.1025?) – 1060; ?Bath Abbey (Wormald)': ([('960 (c.1025?)–1060', [])], [('?Bath Abbey', [WM])]),
    '1028–1070; before 1014 (Wormald); 1006–8 (Rabin)': ([('1028–1070', []), ('before 1014', [WM]), ('1006–8', [RB])], []),
    '685–6; 673–85? (Whitelock)': ([('685–6', []), ('673–85?', [W])], []),
    '1115–33, probably 1131; Westminster (Robertson)': ([('1115–33, probably 1131', [])], [('Westminster', [R])]),
    '1109–11; Reading (Robertson)': ([('1109–11', [])], [('Reading', [R])]),
    'Christmas 1100; Westminster (Robertson)': ([('Christmas 1100', [])], [('Westminster', [R])]),
    '946–c.961 (Liebermann, Robertson); 939–c.961 (Whitelock)': ([('946–c.961', [L, R]), ('939–c.961', [W])], []),
    '925–c.936; before III As (Attenborough)': ([('925–c.936', []), ('before III As', [A])], []),
    '?Date: before III As (Attenborough)': ([('before III As', [A])], []),
    '980–1013; ?same time as III Atr (Robertson); Woodstock, Mercia': ([('980–1013', []), ('?same time as III Atr', [R])], [('Woodstock, Mercia', [])]),
    'Christmas, 1027–34; 1020/21 (Wormald); Winchester; 1020–23 (Whitelock)': ([('Christmas, 1027–34', []), ('1020/21', [WM]), ('1020–23', [W])], [('Winchester', [])]),
    'Easter; Apr. 942–Mar. 946; 942 or 944–6 (Robertson); London': ([('Easter, Apr. 942–Mar. 946', []), ('942 or 944–6', [R])], [('London', [])]),
    '901–24; before 918 (Attenborough)': ([('901–24', []), ('before 918', [A])], []),
    '925–c.935; before III–VI As (Attenborough); Grately; c.926–c.930 (Whitelock)': ([('925–c.935', []), ('before III–VI As', [A]), ('c.926–c.930', [W])], [('Grately', [])]),
    "991; 991 or 994 (Whitelock); mid-990's (Wormald)": ([('991', []), ('991 or 994', [W]), ('mid-990s', [WM])], []),
    "c.1000; (Robertson is silent); mid-990's (Wormald); 991 or 994 (Whitelock)": ([('c.1000', []), ('mid-990s', [WM]), ('991 or 994', [W])], []),
    "991; mid-990's (Wormald); 991 or 994 (Whitelock)": ([('991', []), ('mid-990s', [WM]), ('991 or 994', [W])], []),
    '959–c.962; after IV Edg (Robertson); Andover; 959–63 (Whitelock)': ([('959–c.962', []), ('after IV Eg', [R]), ('959–63', [W])], [('Andover', [])]),
    'c.943–46; no evidence of exact date (Robertson); 939–46 (Whitelock)': ([('c.943–46', []), ('no evidence of exact date', [R]), ('939–46', [W])], []),
    '924–5; before 918 (Attenborough); Exeter': ([('924–5', []), ('before 918', [A])], [('Exeter', [])]),
    'c.928–c.938; after I & V As (Attenborough)': ([('c.928–c.938', []), ('after I & V As', [A])], []),
    "981–1012 or ?997; probably 997 (Whitelock); ?mid–990's (Wormald); Wantage, Wessex": ([('981–1012 or ?997', []), ('probably 997', [W]), ('?mid-990s', [WM])], [('Wantage, Wessex', [])]),
    '940–6; no evidence of date (Robertson); Culinton: ?Colyton, Devonshire': ([('940–6', []), ('no evidence of date', [R])], [('Culinton (?Colyton, Devonshire)', [])]),
    'c.929–939; before VI As (Attenborough); Ðunresfeld': ([('c.929–939', []), ('before VI As', [A])], [('Ðunresfeld', [])]),
    "c.991–c.1002; ?mid-990's (Wormald)": ([('c.991–c.1002', []), ('?mid-990s', [WM])], []),
    '962 –963; 962 or 963 ( Robertson); Wihtbordesstan; 962–3 (Whitelock)': ([('962–963', []), ('962 or 963', [R]), ('962–3', [W])], [('Wihtbordesstan', [])]),
    '980-1016; ? as for VIII Atr (Wormald); Woodstock': ([('980–1016', []), ('?as for VIII Atr', [WM])], [('Woodstock', [])]),
    '688–95; 688–94 (Whitelock)': ([('688–95', []), ('688–94', [W])], []),
    'c.980–c.1050 (Liebermann; ?960 (Wormald)': ([('c.980–c.1050', [L]), ('?960', [WM])], []),
    '1090–1135 (Robertson)': ([('1090–1135', [R])], []),
    'c.1015–c.1050; post–1023 (Wormald); ?1014 (Rabin)': ([('c.1015–c.1050', []), ('after 1023', [WM]), ('?1014', [RB])], []),
    '1028–c.1060; probably 1020–23 (Whitelock)': ([('1028–c.1060', []), ('probably 1020–23', [W])], []),
    'c.936–58, or c.1000; ?c. 930 (Wormald)': ([('c.936–58, or c.1000', []), ('?c.930', [WM])], []),
    "c.910–c.1060 ; ?mid-990's (Wormald)": ([('c.910–c.1060', []), ('?mid-990s', [WM])], []),
    '975 or 978, 14 April; 978 or 979 (Robertson); Kingston, if 978–9 (Robertson)': ([('975 or 978, 14 April', []), ('978 or 979', [R])], [('Kingston, if 978–9', [R])]),
    '960 (c.1025?)–1060; ?Bath Abbey (Wormald)': ([('960 (c.1025?)–1060', [])], [('?Bath Abbey', [WM])]),
    'c.1050; before 959 (Wormald)': ([('c.1050', []), ('before 959', [WM])], []),
    "c.920–c.1050; early 900's (Wormald)": ([('c.920–c.1050', []), ('early 900s', [WM])], []),
    'c.927–937; before III, IV & VI As (Attenborough); Exeter': ([('c.927–937', []), ('before III, IV & VI As', [A])], [('Exeter', [])]),
    '1008; Enham': ([('1008', [])], [('Enham', [])]),
    'c.930–940; after II & V As (Attenborough); London': ([('c.930–940', []), ('after II & V As', [A])], [('London', [])]),
    '16 May 1008 –13 May 1011; 1008 (Robertson, Wormald); Enham': ([('16 May 1008–13 May 1011', []), ('1008', [R, WM])], [('Enham', [])]),
    '16 May 1008 – 13 May 1011; 1008 (Wormald); Enham': ([('16 May 1008–13 May 1011', []), ('1008', [WM])], [('Enham', [])]),
    '992–1011; no evidence of exact date (Robertson); 1009 (Whitelock, Wormald); Bath': ([('992–1011', []), ('no evidence of exact date', [R]), ('1009', [W, WM])], [('Bath', [])]),
    '1014': ([('1014', [])], []),
    'c.910–c.1060 (Liebermann); ?c.995 (Wormald)': ([('c.910–c.1060', [L]), ('?c.995', [WM])], []),
    '944–c.1060; c.945 (Wormald)': ([('944–c.1060', []), ('c.945', [WM])], []),
    '695–6; 6 Sept., 695 (Attenborough); 6 Sept. 695 (Whitelock)': ([('695–6', []), ('6 Sept. 695', [A, W])], []),
    'c.970 (1030?) –c.1060; 1008–1020 (Wormald); no clear indication of date; probably not early (Whitelock)':
        ([('c.970 (1030?)–c.1060', []), ('1008–1020', [WM]), ('no clear indication of date; probably not early', [W])], []),
    '1066–75 (Robertson); London': ([('1066–75', [R])], [('London', [])]),
    'compiled 1110–35 (Robertson)': ([('compiled 1110–35', [R])], []),
    'c. 1210 (Robertson)': ([('c.1210', [R])], []),
    '1070–76, perhaps April 1072 (Robertson)': ([('1070–76, perhaps April 1072', [R])], []),
    '1068–77 (Robertson)': ([('1068–77', [R])], []),
    "1009–1016; ?as for V&VI Atr: 1008 (Wormald); ?King's Enham (Wormald)": ([('1009–1016', []), ('?as for V & VI Atr: 1008', [WM])], [('?King’s Enham', [WM])]),
}

# October 2026: every code’s dates with Liebermann’s first (the date in the running heads of Gesetze I), then
# the other scholars’ in order of publication, Wormald’s (The Making of English Law I, 1999) added where the database
# had none from him. See docs/OE-LAWS.md.
TABLE.update({
    '601–4 (Liebermann); 597–616, perhaps 602–3 (Whitelock); ?614 or just after (Wormald)':
        ([('601–4', [L]), ('597–616, perhaps 602–3', [W]), ('?614 or just after', [WM])], []),
    '685–6 (Liebermann); 673–85? (Whitelock)':
        ([('685–6', [L]), ('673–85?', [W])], []),
    '695–6 (Liebermann); 6 Sept. 695 (Attenborough, Whitelock, Wormald)':
        ([('695–6', [L]), ('6 Sept. 695', [A, W, WM])], []),
    '871 (after 890?)–901 (Liebermann); 885–899 (Whitelock); after 893 (Wormald)':
        ([('871 (after 890?)–901', [L]), ('885–899', [W]), ('after 893', [WM])], []),
    '688–95 (Liebermann); 688–94 (Whitelock); 688×92 (Wormald)':
        ([('688–95', [L]), ('688–94', [W]), ('688×92', [WM])], []),
    '880–90 (Liebermann); 886–90 (Whitelock); before 890, perhaps by over a decade (Wormald)':
        ([('880–90', [L]), ('886–90', [W]), ('before 890, perhaps by over a decade', [WM])], []),
    'Nov. 921–938? (Liebermann); 1002–4 (Wormald, Rabin)':
        ([('Nov. 921–938?', [L]), ('1002–4', [WM, RB])], []),
    '901–24 (Liebermann); before 918 (Attenborough); well before 916 (Wormald)':
        ([('901–24', [L]), ('before 918', [A]), ('well before 916', [WM])], []),
    '924–5 (Liebermann); before 918 (Attenborough); before 916 (Wormald); Exeter':
        ([('924–5', [L]), ('before 918', [A]), ('before 916', [WM])], [('Exeter', [])]),
    '925–c.936 (Liebermann); before III As (Attenborough); early in the reign, before II As (Wormald)':
        ([('925–c.936', [L]), ('before III As', [A]), ('early in the reign, before II As', [WM])], []),
    '925–40 (Liebermann); ?Christmas 932–Jan. 933 (Wormald); before c.1110 (Nowell’s ‘translation’ from Q?)':
        ([('925–40', [L]), ('?Christmas 932–Jan. 933', [WM]), ('before c.1110 (Nowell’s ‘translation’ from Q?)', [])], []),
    '925–c.935 (Liebermann); before III–VI As (Attenborough); c.926–c.930 (Whitelock); not before 928 (Wormald); Grately':
        ([('925–c.935', [L]), ('before III–VI As', [A]), ('c.926–c.930', [W]), ('not before 928', [WM])], [('Grately', [])]),
    'c.928–c.938 (Liebermann); after I & V As (Attenborough); after V As, before VI As 12 (Wormald)':
        ([('c.928–c.938', [L]), ('after I & V As', [A]), ('after V As, before VI As 12', [WM])], []),
    'c.929–c.939 (Liebermann); before VI As (Attenborough); after III As, before VI As 12 (Wormald); Ðunresfeld':
        ([('c.929–c.939', [L]), ('before VI As', [A]), ('after III As, before VI As 12', [WM])], [('Ðunresfeld', [])]),
    'c.927–37 (Liebermann); before III, IV & VI As (Attenborough); Christmas 930, 931 or 934 (Wormald); Exeter':
        ([('c.927–37', [L]), ('before III, IV & VI As', [A]), ('Christmas 930, 931 or 934', [WM])], [('Exeter', [])]),
    'c.930–40 (Liebermann); after II & V As (Attenborough); after IV As, cl. 12 in 934 or 936×7 (Wormald); London':
        ([('c.930–40', [L]), ('after II & V As', [A]), ('after IV As, cl. 12 in 934 or 936×7', [WM])], [('London', [])]),
    'Apr. 942–Mar. 946 (Liebermann); 942 or 944–6 (Robertson); Easter 945 or 946 (Wormald); London':
        ([('Apr. 942–Mar. 946', [L]), ('942 or 944–6', [R]), ('Easter 945 or 946', [WM])], [('London', [])]),
    'c.943–6 (Liebermann); no evidence of exact date (Robertson); 939–46 (Whitelock); after I Em: 945 or 946 (Wormald)':
        ([('c.943–6', [L]), ('no evidence of exact date', [R]), ('939–46', [W]), ('after I Em: 945 or 946', [WM])], []),
    '940–6 (Liebermann); no evidence of date (Robertson); Culinton (?Colyton, Devonshire)':
        ([('940–6', [L]), ('no evidence of date', [R])], [('Culinton (?Colyton, Devonshire)', [])]),
    "946–c.961 (Liebermann, Robertson); 939–c.961 (Whitelock); during or soon after Edmund's reign (Wormald)":
        ([('946–c.961', [L, R]), ('939–c.961', [W]), ("during or soon after Edmund's reign", [WM])], []),
    '959–c.962 (Liebermann); after IV Eg (Robertson); 959–63 (Whitelock); Andover':
        ([('959–c.962', [L]), ('after IV Eg', [R]), ('959–63', [W])], [('Andover', [])]),
    '962–3 (Liebermann, Whitelock); 962 or 963 (Robertson); ?970s (Wormald); Wihtbordesstan':
        ([('962–3', [L, W]), ('962 or 963', [R]), ('?970s', [WM])], [('Wihtbordesstan', [])]),
    '980–1013 (Liebermann); ?same time as III Atr (Robertson); ?mid-990s (Wormald); Woodstock, Mercia':
        ([('980–1013', [L]), ('?same time as III Atr', [R]), ('?mid-990s', [WM])], [('Woodstock, Mercia', [])]),
    '991 (Liebermann); 991 or 994 (Whitelock); mid-990s (Wormald)':
        ([('991', [L]), ('991 or 994', [W]), ('mid-990s', [WM])], []),
    'c.1000 (Liebermann); 991 or 994 (Whitelock); mid-990s (Wormald)':
        ([('c.1000', [L]), ('991 or 994', [W]), ('mid-990s', [WM])], []),
    '981–1012, 997? (Liebermann); probably 997 (Whitelock); ?mid-990s (Wormald); Wantage, Wessex':
        ([('981–1012, 997?', [L]), ('probably 997', [W]), ('?mid-990s', [WM])], [('Wantage, Wessex', [])]),
    'c.991–c.1002 (Liebermann); ?mid-990s (Wormald)':
        ([('c.991–c.1002', [L]), ('?mid-990s', [WM])], []),
    '1008 (Liebermann); Pentecost 1008 (Wormald); Enham':
        ([('1008', [L]), ('Pentecost 1008', [WM])], [('Enham', [])]),
    '16 May 1008–13 May 1011 (Liebermann); 1008 (Robertson, Wormald); Enham':
        ([('16 May 1008–13 May 1011', [L]), ('1008', [R, WM])], [('Enham', [])]),
    '16 May 1008–13 May 1011 (Liebermann); 1008 (Wormald); Enham':
        ([('16 May 1008–13 May 1011', [L]), ('1008', [WM])], [('Enham', [])]),
    '992–1011 (Liebermann); no evidence of exact date (Robertson); 1009 (Whitelock, Wormald); Bath':
        ([('992–1011', [L]), ('no evidence of exact date', [R]), ('1009', [W, WM])], [('Bath', [])]),
    '1014, after Feb. (Liebermann); 1014 (Wormald)':
        ([('1014, after Feb.', [L]), ('1014', [WM])], []),
    'c.980–1016 (Liebermann); ?as for VIII Atr (Wormald); Woodstock':
        ([('c.980–1016', [L]), ('?as for VIII Atr', [WM])], [('Woodstock', [])]),
    '1009–16 (Liebermann); ?as for V & VI Atr: 1008 (Wormald); ?King’s Enham (Wormald)':
        ([('1009–16', [L]), ('?as for V & VI Atr: 1008', [WM])], [('?King’s Enham', [WM])]),
    '1020, Feb.–July (Liebermann); 1019/1020 (Robertson, Wormald); end of 1019 or very beginning of 1020 (Whitelock); England (Robertson); probably written from Denmark (Whitelock)':
        ([('1020, Feb.–July', [L]), ('1019/1020', [R, WM]), ('end of 1019 or very beginning of 1020', [W])], [('England', [R]), ('probably written from Denmark', [W])]),
    '1027, c. May (Liebermann); 1027 (Wormald); ?en route from Rome to Denmark (Robertson)':
        ([('1027, c. May', [L]), ('1027', [WM])], [('?en route from Rome to Denmark', [R])]),
    '25 Dec. 1027–34 (Liebermann); 1020–23 (Whitelock); 1020/21 (Wormald); Winchester':
        ([('25 Dec. 1027–34', [L]), ('1020–23', [W]), ('1020/21', [WM])], [('Winchester', [])]),
    "975 or 978, 14 April (Liebermann); 978 or 979 (Robertson); at Æthelred's consecration (Wormald); Kingston, if 978–9 (Robertson)":
        ([('975 or 978, 14 April', [L]), ('978 or 979', [R]), ("at Æthelred's consecration", [WM])], [('Kingston, if 978–9', [R])]),
    'c.926–c.1000, c.935? (Liebermann); c.930 (Wormald); ?Archenfield, on the Wye (Wormald)':
        ([('c.926–c.1000, c.935?', [L]), ('c.930', [WM])], [('?Archenfield, on the Wye', [WM])]),
    '1028–c.1060 (Liebermann); probably 1020–23 (Whitelock); after 1023 (Wormald)':
        ([('1028–c.1060', [L]), ('probably 1020–23', [W]), ('after 1023', [WM])], []),
    'c.936–58 or –c.1000 (Liebermann); ?c.930 (Wormald)':
        ([('c.936–58 or –c.1000', [L]), ('?c.930', [WM])], []),
    'c.930–75 (Liebermann); ?mid-990s (Wormald)':
        ([('c.930–75', [L]), ('?mid-990s', [WM])], []),
    'c.900–c.1000, c.960? (Liebermann); ?mid-990s (Wormald)':
        ([('c.900–c.1000, c.960?', [L]), ('?mid-990s', [WM])], []),
    'c.910–c.1060 (Liebermann); ?mid-990s (Wormald)':
        ([('c.910–c.1060', [L]), ('?mid-990s', [WM])], []),
    '944–c.1060 (Liebermann); c.945 (Wormald)':
        ([('944–c.1060', [L]), ('c.945', [WM])], []),
    'c.920–c.1050 (Liebermann); early 900s (Wormald)':
        ([('c.920–c.1050', [L]), ('early 900s', [WM])], []),
    'c.1020–c.1060 (Liebermann); c.990–c.1020 (Wormald)':
        ([('c.1020–c.1060', [L]), ('c.990–c.1020', [WM])], []),
    'c.970 (1030?)–c.1060 (Liebermann); no clear indication of date; probably not early (Whitelock); 1008–1020 (Wormald)':
        ([('c.970 (1030?)–c.1060', [L]), ('no clear indication of date; probably not early', [W]), ('1008–1020', [WM])], []),
    '960 (c.1025?)–1060 (Liebermann); ?Bath Abbey (Wormald)':
        ([('960 (c.1025?)–1060', [L])], [('?Bath Abbey', [WM])]),
    '960 (c.1025)–1060 (Liebermann); ?Bath Abbey (Wormald)':
        ([('960 (c.1025)–1060', [L])], [('?Bath Abbey', [WM])]),
    'c.1029–c.1060 (Liebermann); 1002–23 (Whitelock); 1006–8 (Rabin)':
        ([('c.1029–c.1060', [L]), ('1002–23', [W]), ('1006–8', [RB])], []),
    'c.920–954 (Liebermann); 1002–23 (Whitelock); 1006–8 (Rabin)':
        ([('c.920–954', [L]), ('1002–23', [W]), ('1006–8', [RB])], []),
    'c.920–c.970 (Liebermann); 1002–23 (Whitelock); 1006–8 (Rabin)':
        ([('c.920–c.970', [L]), ('1002–23', [W]), ('1006–8', [RB])], []),
    'c.950–c.1050 (Liebermann); 1002–23 (Whitelock); 1006–8 (Rabin)':
        ([('c.950–c.1050', [L]), ('1002–23', [W]), ('1006–8', [RB])], []),
    'c.1030–c.1050 (Liebermann); 1002–23 (Whitelock); before 1014 (Wormald); 1006–8 (Rabin)':
        ([('c.1030–c.1050', [L]), ('1002–23', [W]), ('before 1014', [WM]), ('1006–8', [RB])], []),
    '1028–1070 (Liebermann); before 1014 (Wormald); 1006–8 (Rabin)':
        ([('1028–1070', [L]), ('before 1014', [WM]), ('1006–8', [RB])], []),
    'c.1015–c.1050 (Liebermann); after 1023 (Wormald); ?1014 (Rabin)':
        ([('c.1015–c.1050', [L]), ('after 1023', [WM]), ('?1014', [RB])], []),
    'c.1050 (Liebermann); before 959 (Wormald)':
        ([('c.1050', [L]), ('before 959', [WM])], []),
    'c.980–c.1050 (Liebermann); ?960 (Wormald)':
        ([('c.980–c.1050', [L]), ('?960', [WM])], []),
    'c.1000–1050 (Liebermann); 1002×1008 (Rabin)':
        ([('c.1000–1050', [L]), ('1002×1008', [RB])], []),
    'c.950–1050 (Liebermann)':
        ([('c.950–1050', [L])], []),
    'c.890–c.940 (Liebermann)':
        ([('c.890–c.940', [L])], []),
    'c.945, the work excerpted (Wormald)':
        ([('c.945, the work excerpted', [WM])], []),
    'Dec. 1066–75 (Liebermann); 1066–75 (Robertson); 1066/7, within months of the coronation (Wormald); London':
        ([('Dec. 1066–75', [L]), ('1066–75', [R]), ('1066/7, within months of the coronation', [WM])], [('London', [])]),
    '1067–77 (Liebermann); 1068–77 (Robertson)':
        ([('1067–77', [L]), ('1068–77', [R])], []),
    '1070–76, perhaps April 1072 (Liebermann, Robertson); after 1070 (Wormald)':
        ([('1070–76, perhaps April 1072', [L, R]), ('after 1070', [WM])], []),
    "compiled c.1110–35 (Liebermann); compiled 1110–35 (Robertson); late in William I's reign (Wormald)":
        ([('compiled c.1110–35', [L]), ('compiled 1110–35', [R]), ("late in William I's reign", [WM])], []),
    'c.1210 (Liebermann, Robertson)':
        ([('c.1210', [L, R])], []),
    '1090–1135 (Liebermann, Robertson); mid-12th century (Wormald)':
        ([('1090–1135', [L, R]), ('mid-12th century', [WM])], []),
    '5 Aug. 1100 (Liebermann); Westminster (Robertson)':
        ([('5 Aug. 1100', [L])], [('Westminster', [R])]),
    '1100–3 (Liebermann); Westminster (Robertson)':
        ([('1100–3', [L])], [('Westminster', [R])]),
    '1109–11 (Liebermann); 1108 (Wormald); Reading (Robertson)':
        ([('1109–11', [L]), ('1108', [WM])], [('Reading', [R])]),
    "1115–33, probably 1131 (Liebermann); very late in Henry I's reign (Wormald); Westminster (Robertson)":
        ([('1115–33, probably 1131', [L]), ("very late in Henry I's reign", [WM])], [('Westminster', [R])]),
})

# 19 October 2026: the same dates with the page where each scholar gives them: Liebermann's page in Gesetze I (where
# his date for the code is printed) and Wormald's in The Making of English Law I. A scholar is then "Name, page".
TABLE.update({
    '601–4 (Liebermann, I p. 3); 597–616, perhaps 602–3 (Whitelock, EHD p. 390); ?614 or just after (Wormald, MEL pp. 100–1)':
        ([('601–4', ['Liebermann, I p. 3']), ('597–616, perhaps 602–3', ['Whitelock, EHD p. 390']), ('?614 or just after', ['Wormald, MEL pp. 100–1'])], []),
    '685–6 (Liebermann, I p. 9); 673–85? (Whitelock, EHD p. 393)':
        ([('685–6', ['Liebermann, I p. 9']), ('673–85?', ['Whitelock, EHD p. 393'])], []),
    '695–6 (Liebermann, I p. 12); 6 Sept. 695 (Attenborough; Whitelock, EHD p. 396; Wormald, MEL p. 102)':
        ([('695–6', ['Liebermann, I p. 12']), ('6 Sept. 695', ['Attenborough', 'Whitelock, EHD p. 396', 'Wormald, MEL p. 102'])], []),
    'c.890–c.940 (Liebermann, I p. 16)':
        ([('c.890–c.940', ['Liebermann, I p. 16'])], []),
    'c.890–c.940 (Liebermann, I p. 20)':
        ([('c.890–c.940', ['Liebermann, I p. 20'])], []),
    '871 (after 890?)–901 (Liebermann, I p. 27); 885–899 (Whitelock, EHD p. 408); after 893 (Wormald, MEL p. 286)':
        ([('871 (after 890?)–901', ['Liebermann, I p. 27']), ('885–899', ['Whitelock, EHD p. 408']), ('after 893', ['Wormald, MEL p. 286'])], []),
    '688–95 (Liebermann, I p. 88); 688–94 (Whitelock, EHD p. 399); 688×92 (Wormald, MEL p. 103)':
        ([('688–95', ['Liebermann, I p. 88']), ('688–94', ['Whitelock, EHD p. 399']), ('688×92', ['Wormald, MEL p. 103'])], []),
    '880–90 (Liebermann, I p. 126); 886–90 (Whitelock, EHD p. 417); before 890, perhaps by over a decade (Wormald, MEL p. 286)':
        ([('880–90', ['Liebermann, I p. 126']), ('886–90', ['Whitelock, EHD p. 417']), ('before 890, perhaps by over a decade', ['Wormald, MEL p. 286'])], []),
    'Nov. 921–938? (Liebermann, I p. 128); 1002–4 (Wormald, MEL pp. 389–91; Rabin)':
        ([('Nov. 921–938?', ['Liebermann, I p. 128']), ('1002–4', ['Wormald, MEL pp. 389–91', 'Rabin'])], []),
    '901–24 (Liebermann, I p. 138); before 918 (Attenborough); well before 916 (Wormald, MEL pp. 438–9)':
        ([('901–24', ['Liebermann, I p. 138']), ('before 918', ['Attenborough']), ('well before 916', ['Wormald, MEL pp. 438–9'])], []),
    '924–5 (Liebermann, I p. 140); before 918 (Attenborough); before 916 (Wormald, MEL pp. 438–9); Exeter':
        ([('924–5', ['Liebermann, I p. 140']), ('before 918', ['Attenborough']), ('before 916', ['Wormald, MEL pp. 438–9'])], [('Exeter', [])]),
    '925–c.936 (Liebermann, I p. 146); before III As (Attenborough); early in the reign, before II As (Wormald, MEL p. 439)':
        ([('925–c.936', ['Liebermann, I p. 146']), ('before III As', ['Attenborough']), ('early in the reign, before II As', ['Wormald, MEL p. 439'])], []),
    '925–40 (Liebermann, I p. 148); ?Christmas 932–Jan. 933 (Wormald, MEL p. 439 n. 76); before c.1110 (Nowell’s ‘translation’ from Q?)':
        ([('925–40', ['Liebermann, I p. 148']), ('?Christmas 932–Jan. 933', ['Wormald, MEL p. 439 n. 76']), ('before c.1110 (Nowell’s ‘translation’ from Q?)', [])], []),
    '925–c.935 (Liebermann, I p. 150); before III–VI As (Attenborough); c.926–c.930 (Whitelock, EHD p. 418); not before 928 (Wormald, MEL p. 440); Grately':
        ([('925–c.935', ['Liebermann, I p. 150']), ('before III–VI As', ['Attenborough']), ('c.926–c.930', ['Whitelock, EHD p. 418']), ('not before 928', ['Wormald, MEL p. 440'])], [('Grately', [])]),
    'c.928–c.938 (Liebermann, I p. 170); after I & V As (Attenborough); after V As, before VI As 12 (Wormald, MEL pp. 439–40)':
        ([('c.928–c.938', ['Liebermann, I p. 170']), ('after I & V As', ['Attenborough']), ('after V As, before VI As 12', ['Wormald, MEL pp. 439–40'])], []),
    'c.929–c.939 (Liebermann, I p. 171); before VI As (Attenborough); after III As, before VI As 12 (Wormald, MEL pp. 439–40); Ðunresfeld':
        ([('c.929–c.939', ['Liebermann, I p. 171']), ('before VI As', ['Attenborough']), ('after III As, before VI As 12', ['Wormald, MEL pp. 439–40'])], [('Ðunresfeld', [])]),
    'c.927–37 (Liebermann, I p. 166); before III, IV & VI As (Attenborough); before III and IV As (Whitelock, EHD p. 423); Christmas 930, 931 or 934 (Wormald, MEL p. 439); Exeter':
        ([('c.927–37', ['Liebermann, I p. 166']), ('before III, IV & VI As', ['Attenborough']), ('before III and IV As', ['Whitelock, EHD p. 423']), ('Christmas 930, 931 or 934', ['Wormald, MEL p. 439'])], [('Exeter', [])]),
    'c.930–40 (Liebermann, I p. 173); after II & V As (Attenborough); after IV As, cl. 12 in 934 or 936×7 (Wormald, MEL pp. 439–40); London':
        ([('c.930–40', ['Liebermann, I p. 173']), ('after II & V As', ['Attenborough']), ('after IV As, cl. 12 in 934 or 936×7', ['Wormald, MEL pp. 439–40'])], [('London', [])]),
    'Apr. 942–Mar. 946 (Liebermann, I p. 184); 942 or 944–6 (Robertson); Easter 945 or 946 (Wormald, MEL p. 441); London':
        ([('Apr. 942–Mar. 946', ['Liebermann, I p. 184']), ('942 or 944–6', ['Robertson']), ('Easter 945 or 946', ['Wormald, MEL p. 441'])], [('London', [])]),
    'c.943–6 (Liebermann, I p. 186); no evidence of exact date (Robertson); 939–46 (Whitelock, EHD p. 429); after I Em: 945 or 946 (Wormald, MEL pp. 440–1)':
        ([('c.943–6', ['Liebermann, I p. 186']), ('no evidence of exact date', ['Robertson']), ('939–46', ['Whitelock, EHD p. 429']), ('after I Em: 945 or 946', ['Wormald, MEL pp. 440–1'])], []),
    '940–6 (Liebermann, I p. 190); no evidence of date (Robertson); Culinton (?Colyton, Devonshire)':
        ([('940–6', ['Liebermann, I p. 190']), ('no evidence of date', ['Robertson'])], [('Culinton (?Colyton, Devonshire)', [])]),
    "946–c.961 (Liebermann, I p. 192; Robertson); 939–c.961 (Whitelock, EHD p. 431); during or soon after Edmund's reign (Wormald, MEL p. 378)":
        ([('946–c.961', ['Liebermann, I p. 192', 'Robertson']), ('939–c.961', ['Whitelock, EHD p. 431']), ("during or soon after Edmund's reign", ['Wormald, MEL p. 378'])], []),
    '959–c.962 (Liebermann, I p. 194); after IV Eg (Robertson); 959–63 (Whitelock, EHD p. 434); Andover':
        ([('959–c.962', ['Liebermann, I p. 194']), ('after IV Eg', ['Robertson']), ('959–63', ['Whitelock, EHD p. 434'])], [('Andover', [])]),
    '959–c.962 (Liebermann, I p. 200); after IV Eg (Robertson); 959–63 (Whitelock, EHD p. 434); Andover':
        ([('959–c.962', ['Liebermann, I p. 200']), ('after IV Eg', ['Robertson']), ('959–63', ['Whitelock, EHD p. 434'])], [('Andover', [])]),
    '962–3 (Liebermann, I p. 206; Whitelock, EHD p. 437); 962 or 963 (Robertson); ?970s (Wormald, MEL pp. 441–2); Wihtbordesstan':
        ([('962–3', ['Liebermann, I p. 206', 'Whitelock, EHD p. 437']), ('962 or 963', ['Robertson']), ('?970s', ['Wormald, MEL pp. 441–2'])], [('Wihtbordesstan', [])]),
    '980–1013 (Liebermann, I p. 216); ?same time as III Atr (Robertson); ?mid-990s (Wormald, MEL p. 443); Woodstock, Mercia':
        ([('980–1013', ['Liebermann, I p. 216']), ('?same time as III Atr', ['Robertson']), ('?mid-990s', ['Wormald, MEL p. 443'])], [('Woodstock, Mercia', [])]),
    '991 (Liebermann, I p. 220); 991 or 994 (Whitelock, EHD p. 441); mid-990s (Wormald, MEL p. 321)':
        ([('991', ['Liebermann, I p. 220']), ('991 or 994', ['Whitelock, EHD p. 441']), ('mid-990s', ['Wormald, MEL p. 321'])], []),
    'c.1000 (Liebermann, I p. 220); 991 or 994 (Whitelock, EHD p. 441); mid-990s (Wormald, MEL p. 321)':
        ([('c.1000', ['Liebermann, I p. 220']), ('991 or 994', ['Whitelock, EHD p. 441']), ('mid-990s', ['Wormald, MEL p. 321'])], []),
    '981–1012, 997? (Liebermann, I p. 228); probably 997 (Whitelock, EHD p. 444); ?mid-990s (Wormald, MEL p. 443); Wantage, Wessex':
        ([('981–1012, 997?', ['Liebermann, I p. 228']), ('probably 997', ['Whitelock, EHD p. 444']), ('?mid-990s', ['Wormald, MEL p. 443'])], [('Wantage, Wessex', [])]),
    'c.991–c.1002 (Liebermann, I p. 232); ?mid-990s (Wormald, MEL p. 443)':
        ([('c.991–c.1002', ['Liebermann, I p. 232']), ('?mid-990s', ['Wormald, MEL p. 443'])], []),
    '1008 (Liebermann, I p. 236; Whitelock, EHD p. 447); Pentecost 1008 (Wormald, MEL p. 332); Enham':
        ([('1008', ['Liebermann, I p. 236', 'Whitelock, EHD p. 447']), ('Pentecost 1008', ['Wormald, MEL p. 332'])], [('Enham', [])]),
    '16 May 1008–13 May 1011 (Liebermann, I p. 246); 1008 (Robertson; Wormald, MEL pp. 332–5); Enham':
        ([('16 May 1008–13 May 1011', ['Liebermann, I p. 246']), ('1008', ['Robertson', 'Wormald, MEL pp. 332–5'])], [('Enham', [])]),
    '16 May 1008–13 May 1011 (Liebermann, I p. 247); 1008 (Wormald, MEL pp. 333–5); Enham':
        ([('16 May 1008–13 May 1011', ['Liebermann, I p. 247']), ('1008', ['Wormald, MEL pp. 333–5'])], [('Enham', [])]),
    '992–1011 (Liebermann, I p. 260); no evidence of exact date (Robertson); probably 1009 (Whitelock, EHD p. 452); 1009 (Wormald, MEL p. 331); Bath':
        ([('992–1011', ['Liebermann, I p. 260']), ('no evidence of exact date', ['Robertson']), ('probably 1009', ['Whitelock, EHD p. 452']), ('1009', ['Wormald, MEL p. 331'])], [('Bath', [])]),
    '992–1011 (Liebermann, I p. 262); no evidence of exact date (Robertson); probably 1009 (Whitelock, EHD p. 452); 1009 (Wormald, MEL pp. 331–2); Bath':
        ([('992–1011', ['Liebermann, I p. 262']), ('no evidence of exact date', ['Robertson']), ('probably 1009', ['Whitelock, EHD p. 452']), ('1009', ['Wormald, MEL pp. 331–2'])], [('Bath', [])]),
    '1014, after Feb. (Liebermann, I p. 263); 1014 (Whitelock, EHD p. 454; Wormald, MEL p. 336)':
        ([('1014, after Feb.', ['Liebermann, I p. 263']), ('1014', ['Whitelock, EHD p. 454', 'Wormald, MEL p. 336'])], []),
    'c.980–1016 (Liebermann, I p. 269); ? as for VIII Atr, i.e. 1014 (Wormald, MEL pp. 337, 431); Woodstock':
        ([('c.980–1016', ['Liebermann, I p. 269']), ('? as for VIII Atr, i.e. 1014', ['Wormald, MEL pp. 337, 431'])], [('Woodstock', [])]),
    '1009–16 (Liebermann, I p. 269); ?as for V & VI Atr: 1008 (Wormald, MEL pp. 336–7); ?King’s Enham (Wormald, MEL pp. 336–7)':
        ([('1009–16', ['Liebermann, I p. 269']), ('?as for V & VI Atr: 1008', ['Wormald, MEL pp. 336–7'])], [('?King’s Enham', ['Wormald, MEL pp. 336–7'])]),
    '1018 (Whitelock, EHD p. 458; Kennedy; Wormald, MEL p. 346); Oxford':
        ([('1018', ['Whitelock, EHD p. 458', 'Kennedy', 'Wormald, MEL p. 346'])], [('Oxford', [])]),
    '1020, Feb.–July (Liebermann, I p. 273); 1019/1020 (Robertson; Wormald, MEL p. 347); end of 1019 or very beginning of 1020 (Whitelock, EHD p. 459); England (Robertson); probably written from Denmark (Whitelock, EHD p. 459)':
        ([('1020, Feb.–July', ['Liebermann, I p. 273']), ('1019/1020', ['Robertson', 'Wormald, MEL p. 347']), ('end of 1019 or very beginning of 1020', ['Whitelock, EHD p. 459'])], [('England', ['Robertson']), ('probably written from Denmark', ['Whitelock, EHD p. 459'])]),
    '1027, c. May (Liebermann, I p. 276); 1027 (Whitelock, EHD p. 485; Wormald, MEL p. 348); ?en route from Rome to Denmark (Robertson)':
        ([('1027, c. May', ['Liebermann, I p. 276']), ('1027', ['Whitelock, EHD p. 485', 'Wormald, MEL p. 348'])], [('?en route from Rome to Denmark', ['Robertson'])]),
    '25 Dec. 1027–34 (Liebermann, I p. 278); 1020–23 (Whitelock, EHD p. 461); 1020/21 (Wormald, MEL p. 345); Winchester':
        ([('25 Dec. 1027–34', ['Liebermann, I p. 278']), ('1020–23', ['Whitelock, EHD p. 461']), ('1020/21', ['Wormald, MEL p. 345'])], [('Winchester', [])]),
    '25 Dec. 1027–34 (Liebermann, I p. 308); 1020–23 (Whitelock, EHD p. 461); 1020/21 (Wormald, MEL p. 345); Winchester':
        ([('25 Dec. 1027–34', ['Liebermann, I p. 308']), ('1020–23', ['Whitelock, EHD p. 461']), ('1020/21', ['Wormald, MEL p. 345'])], [('Winchester', [])]),
    "975 or 978, 14 April (Liebermann, I p. 214); 978 or 979 (Robertson); at Æthelred's consecration (Wormald, MEL pp. 447–8); Kingston, if 978–9 (Robertson)":
        ([('975 or 978, 14 April', ['Liebermann, I p. 214']), ('978 or 979', ['Robertson']), ("at Æthelred's consecration", ['Wormald, MEL pp. 447–8'])], [('Kingston, if 978–9', ['Robertson'])]),
    'c.926–c.1000, c.935? (Liebermann, I p. 374); c.930 (Wormald, MEL pp. 381–2); ?Archenfield, on the Wye (Wormald, MEL pp. 381–2)':
        ([('c.926–c.1000, c.935?', ['Liebermann, I p. 374']), ('c.930', ['Wormald, MEL pp. 381–2'])], [('?Archenfield, on the Wye', ['Wormald, MEL pp. 381–2'])]),
    '1028–c.1060 (Liebermann, I p. 380); probably 1020–23 (Whitelock, EHD p. 479); after 1023 (Wormald, MEL pp. 396–7)':
        ([('1028–c.1060', ['Liebermann, I p. 380']), ('probably 1020–23', ['Whitelock, EHD p. 479']), ('after 1023', ['Wormald, MEL pp. 396–7'])], []),
    'c.936–58 or –c.1000 (Liebermann, I p. 386); ?c.930 (Wormald, MEL pp. 373–4)':
        ([('c.936–58 or –c.1000', ['Liebermann, I p. 386']), ('?c.930', ['Wormald, MEL pp. 373–4'])], []),
    'c.930–75 (Liebermann, I p. 388); ?mid-990s (Wormald)':
        ([('c.930–75', ['Liebermann, I p. 388']), ('?mid-990s', ['Wormald'])], []),
    'c.900–c.1000, c.960? (Liebermann, I p. 388); ?mid-990s (Wormald)':
        ([('c.900–c.1000, c.960?', ['Liebermann, I p. 388']), ('?mid-990s', ['Wormald'])], []),
    'c.910–c.1060 (Liebermann, I p. 390); ?mid-990s (Wormald, MEL pp. 371–2)':
        ([('c.910–c.1060', ['Liebermann, I p. 390']), ('?mid-990s', ['Wormald, MEL pp. 371–2'])], []),
    'c.910–c.1060 (Liebermann, I p. 392); ?c.995 (Wormald, MEL pp. 371–2)':
        ([('c.910–c.1060', ['Liebermann, I p. 392']), ('?c.995', ['Wormald, MEL pp. 371–2'])], []),
    '944–c.1060 (Liebermann, I p. 392); c.945 (Wormald, MEL pp. 374–8)':
        ([('944–c.1060', ['Liebermann, I p. 392']), ('c.945', ['Wormald, MEL pp. 374–8'])], []),
    'c.920–c.1050 (Liebermann, I p. 396); early 900s (Wormald, MEL p. 384)':
        ([('c.920–c.1050', ['Liebermann, I p. 396']), ('early 900s', ['Wormald, MEL p. 384'])], []),
    'c.1020–c.1060 (Liebermann, I p. 400); c.990–c.1020 (Wormald, MEL p. 385)':
        ([('c.1020–c.1060', ['Liebermann, I p. 400']), ('c.990–c.1020', ['Wormald, MEL p. 385'])], []),
    'c.970 (1030?)–c.1060 (Liebermann, I p. 442); no clear indication of date; probably not early (Whitelock, EHD p. 474); 1008–1020 (Wormald, MEL p. 386)':
        ([('c.970 (1030?)–c.1060', ['Liebermann, I p. 442']), ('no clear indication of date; probably not early', ['Whitelock, EHD p. 474']), ('1008–1020', ['Wormald, MEL p. 386'])], []),
    '960 (c.1025?)–1060 (Liebermann, I p. 444); ?Bath Abbey (Wormald, MEL p. 389)':
        ([('960 (c.1025?)–1060', ['Liebermann, I p. 444'])], [('?Bath Abbey', ['Wormald, MEL p. 389'])]),
    '960 (c.1025)–1060 (Liebermann, I p. 453); ?Bath Abbey (Wormald)':
        ([('960 (c.1025)–1060', ['Liebermann, I p. 453'])], [('?Bath Abbey', ['Wormald'])]),
    'c.1029–c.1060 (Liebermann, I p. 456); 1002–23 (Whitelock, EHD p. 475); 1006–8 (Rabin)':
        ([('c.1029–c.1060', ['Liebermann, I p. 456']), ('1002–23', ['Whitelock, EHD p. 475']), ('1006–8', ['Rabin'])], []),
    'c.920–954 (Liebermann, I p. 458); 1002–23 (Whitelock, EHD p. 475); 1006–8 (Rabin)':
        ([('c.920–954', ['Liebermann, I p. 458']), ('1002–23', ['Whitelock, EHD p. 475']), ('1006–8', ['Rabin'])], []),
    'c.920–c.970 (Liebermann, I p. 462); 1002–23 (Whitelock, EHD p. 475); 1006–8 (Rabin)':
        ([('c.920–c.970', ['Liebermann, I p. 462']), ('1002–23', ['Whitelock, EHD p. 475']), ('1006–8', ['Rabin'])], []),
    'c.950–c.1050 (Liebermann, I p. 464); 1002–23 (Whitelock, EHD p. 475); 1006–8 (Rabin)':
        ([('c.950–c.1050', ['Liebermann, I p. 464']), ('1002–23', ['Whitelock, EHD p. 475']), ('1006–8', ['Rabin'])], []),
    'c.1030–c.1050 (Liebermann, I p. 464); 1002–23 (Whitelock, EHD p. 475); before 1014 (Wormald, MEL pp. 390, 393, 395); 1006–8 (Rabin)':
        ([('c.1030–c.1050', ['Liebermann, I p. 464']), ('1002–23', ['Whitelock, EHD p. 475']), ('before 1014', ['Wormald, MEL pp. 390, 393, 395']), ('1006–8', ['Rabin'])], []),
    '1028–1070 (Liebermann, I p. 470); before 1014 (Wormald, MEL pp. 394–5); 1006–8 (Rabin)':
        ([('1028–1070', ['Liebermann, I p. 470']), ('before 1014', ['Wormald, MEL pp. 394–5']), ('1006–8', ['Rabin'])], []),
    'c.1015–c.1050 (Liebermann, I p. 473); after 1023 (Wormald); ?1014 (Rabin)':
        ([('c.1015–c.1050', ['Liebermann, I p. 473']), ('after 1023', ['Wormald']), ('?1014', ['Rabin'])], []),
    'c.1050 (Liebermann, I p. 474); before 959 (Wormald, MEL p. 368)':
        ([('c.1050', ['Liebermann, I p. 474']), ('before 959', ['Wormald, MEL p. 368'])], []),
    'c.980–c.1050 (Liebermann, I p. 474); ?960 (Wormald, MEL p. 383)':
        ([('c.980–c.1050', ['Liebermann, I p. 474']), ('?960', ['Wormald, MEL p. 383'])], []),
    'c.1000–1050 (Liebermann, I p. 477); 1002×1008 (Rabin)':
        ([('c.1000–1050', ['Liebermann, I p. 477']), ('1002×1008', ['Rabin'])], []),
    'c.950–1050 (Liebermann, I p. 415)':
        ([('c.950–1050', ['Liebermann, I p. 415'])], []),
    'c.945, the work excerpted (Wormald, MEL pp. 372–3)':
        ([('c.945, the work excerpted', ['Wormald, MEL pp. 372–3'])], []),
    'Dec. 1066–75 (Liebermann, I p. 486); 1066–75 (Robertson); 1066/7, within months of the coronation (Wormald, MEL p. 398); London':
        ([('Dec. 1066–75', ['Liebermann, I p. 486']), ('1066–75', ['Robertson']), ('1066/7, within months of the coronation', ['Wormald, MEL p. 398'])], [('London', [])]),
    '1067–77 (Liebermann, I p. 483); 1068–77 (Robertson)':
        ([('1067–77', ['Liebermann, I p. 483']), ('1068–77', ['Robertson'])], []),
    '1070–76, perhaps April 1072 (Liebermann, I p. 485; Robertson); after 1070 (Wormald, MEL p. 399)':
        ([('1070–76, perhaps April 1072', ['Liebermann, I p. 485', 'Robertson']), ('after 1070', ['Wormald, MEL p. 399'])], []),
    "compiled c.1110–35 (Liebermann, I p. 486); compiled 1110–35 (Robertson); late in William I's reign (Wormald, MEL pp. 402–5)":
        ([('compiled c.1110–35', ['Liebermann, I p. 486']), ('compiled 1110–35', ['Robertson']), ("late in William I's reign", ['Wormald, MEL pp. 402–5'])], []),
    'c.1210 (Liebermann, I p. 489; Robertson)':
        ([('c.1210', ['Liebermann, I p. 489', 'Robertson'])], []),
    'c. 1210 (Liebermann, I p. 489)':
        ([('c. 1210', ['Liebermann, I p. 489'])], []),
    '1090–1135 (Liebermann, I p. 492; Robertson); mid-12th century (Wormald, MEL pp. 407–9)':
        ([('1090–1135', ['Liebermann, I p. 492', 'Robertson']), ('mid-12th century', ['Wormald, MEL pp. 407–9'])], []),
    '1090–1135 (Liebermann, I p. 492)':
        ([('1090–1135', ['Liebermann, I p. 492'])], []),
    '5 Aug. 1100 (Liebermann, I p. 521); Westminster (Robertson)':
        ([('5 Aug. 1100', ['Liebermann, I p. 521'])], [('Westminster', ['Robertson'])]),
    '1100, 5 Aug. (Liebermann, I p. 521)':
        ([('1100, 5 Aug.', ['Liebermann, I p. 521'])], []),
    '1100–3 (Liebermann, I p. 523); Westminster (Robertson)':
        ([('1100–3', ['Liebermann, I p. 523'])], [('Westminster', ['Robertson'])]),
    '1109–11 (Liebermann, I p. 524); 1108 (Wormald, MEL p. 401); Reading (Robertson)':
        ([('1109–11', ['Liebermann, I p. 524']), ('1108', ['Wormald, MEL p. 401'])], [('Reading', ['Robertson'])]),
    "1115–33, probably 1131 (Liebermann, I p. 524); very late in Henry I's reign (Wormald, MEL p. 401); Westminster (Robertson)":
        ([('1115–33, probably 1131', ['Liebermann, I p. 524']), ("very late in Henry I's reign", ['Wormald, MEL p. 401'])], [('Westminster', ['Robertson'])]),
    '640–664 (Liebermann, I p. 9)':
        ([('640–664', ['Liebermann, I p. 9'])], []),
    'c. 930–1060, probably 940–56 (Liebermann, I p. 394)':
        ([('c. 930–1060, probably 940–56', ['Liebermann, I p. 394'])], []),
    'c. 850–c. 975 (Liebermann, I p. 401)':
        ([('c. 850–c. 975', ['Liebermann, I p. 401'])], []),
    'c. 850–c. 975 (Liebermann, I p. 406)':
        ([('c. 850–c. 975', ['Liebermann, I p. 406'])], []),
    'c. 850–c. 975 (Liebermann, I p. 408)':
        ([('c. 850–c. 975', ['Liebermann, I p. 408'])], []),
    'c. 9th century (Liebermann, I p. 409)':
        ([('c. 9th century', ['Liebermann, I p. 409'])], []),
    'c. 9th century (Liebermann, I p. 411)':
        ([('c. 9th century', ['Liebermann, I p. 411'])], []),
    'c. 9th century (Liebermann, I p. 412)':
        ([('c. 9th century', ['Liebermann, I p. 412'])], []),
    'c. 950–1050 (Liebermann, I p. 413)':
        ([('c. 950–1050', ['Liebermann, I p. 413'])], []),
    'c. 850–c. 975 (Liebermann, I p. 416)':
        ([('c. 850–c. 975', ['Liebermann, I p. 416'])], []),
    '1067–c. 1150 (Liebermann, I p. 417)':
        ([('1067–c. 1150', ['Liebermann, I p. 417'])], []),
    '1067?–1125 (Liebermann, I p. 419)':
        ([('1067?–1125', ['Liebermann, I p. 419'])], []),
    '1067?–c. 1125 (Liebermann, I p. 420)':
        ([('1067?–c. 1125', ['Liebermann, I p. 420'])], []),
    '1067?–1125 (Liebermann, I p. 422)':
        ([('1067?–1125', ['Liebermann, I p. 422'])], []),
    '1067?–c. 1125 (Liebermann, I p. 425)':
        ([('1067?–c. 1125', ['Liebermann, I p. 425'])], []),
    '1067–c. 1210 (Liebermann, I p. 427)':
        ([('1067–c. 1210', ['Liebermann, I p. 427'])], []),
    '1067–c. 1130 (Liebermann, I p. 430)':
        ([('1067–c. 1130', ['Liebermann, I p. 430'])], []),
    'Frankish, before 910; in England before 1075 (Liebermann, I p. 432)':
        ([('Frankish, before 910', []), ('in England before 1075', ['Liebermann, I p. 432'])], []),
    'Frankish, before 910; in England before 1350 (Liebermann, I p. 434)':
        ([('Frankish, before 910', []), ('in England before 1350', ['Liebermann, I p. 434'])], []),
    'c. 700–c. 1050 (Liebermann, I p. 434)':
        ([('c. 700–c. 1050', ['Liebermann, I p. 434'])], []),
    'c. 900–c. 1050 (Liebermann, I p. 435)':
        ([('c. 900–c. 1050', ['Liebermann, I p. 435'])], []),
    'c. 900–c. 1050 (Liebermann, I p. 436)':
        ([('c. 900–c. 1050', ['Liebermann, I p. 436'])], []),
    'c. 950–c. 1100 (Liebermann, I p. 438)':
        ([('c. 950–c. 1100', ['Liebermann, I p. 438'])], []),
    'c. 900–c. 1100 (Liebermann, I p. 439)':
        ([('c. 900–c. 1100', ['Liebermann, I p. 439'])], []),
    'c. 900–c. 1100 (Liebermann, I p. 440)':
        ([('c. 900–c. 1100', ['Liebermann, I p. 440'])], []),
    'c. 1000–c. 1200 (Liebermann, I p. 440)':
        ([('c. 1000–c. 1200', ['Liebermann, I p. 440'])], []),
    'c. 1000–c. 1300 (Liebermann, I p. 441)':
        ([('c. 1000–c. 1300', ['Liebermann, I p. 441'])], []),
    'c. 900–c. 1100 (Liebermann, I p. 441)':
        ([('c. 900–c. 1100', ['Liebermann, I p. 441'])], []),
    '1192/3 (Liebermann, I p. 488)':
        ([('1192/3', ['Liebermann, I p. 488'])], []),
    'c. 1110 (Liebermann, I p. 520)':
        ([('c. 1110', ['Liebermann, I p. 520'])], []),
})

KNOWN = {W, WM, R, A, RB, K, L}


def _key(text):
    return re.sub(r'\s+', ' ', html.unescape(text or '')).strip()


def _auto(text):
    dates, places = [], []
    for part in [p.strip() for p in text.split(';') if p.strip()]:
        m = re.match(r'^(.*?)\s*\(([^()]*)\)\.?$', part)
        who = []
        if m and all(n.strip() in KNOWN for n in m.group(2).split(',')):
            part, who = m.group(1).strip(), [n.strip() for n in m.group(2).split(',')]
        (dates if re.search(r'\d', part) else places).append((part, who))
    return dates, places


def split_who(entry):
    """'Wormald, MEL p. 337' -> ('Wormald', 'MEL p. 337'); 'Whitelock' -> ('Whitelock', '')"""
    name, _, page = entry.partition(', ')
    return name, page


def parse(text):
    """([(date, [scholars])], [(place, [scholars])]) for one spreadsheet string. A scholar may carry a page:
    'Wormald, MEL p. 337' (see split_who)."""
    key = _key(text)
    if not key:
        return [], []
    return TABLE.get(key) or _auto(key)
