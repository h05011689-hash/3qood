<?php

// By Mohamed Eltohamy 


ob_start();
include("config.php");
define("API_KEY",$API_KEY);
function bot($method,$datas=[]){
$url = "https://api.telegram.org/bot".API_KEY."/".$method;
$ch = curl_init();
    curl_setopt($ch,CURLOPT_URL,$url);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_setopt($ch,CURLOPT_POSTFIELDS,$datas);
    $res = curl_exec($ch);
    if(curl_error($ch)){
        var_dump(curl_error($ch));
    }else{
        return json_decode($res);
    }
}
$update = json_decode(file_get_contents('php://input'));

$message = $update->message;
$chat_id = $message->chat->id;
$text = $message->text;
$message_id = $message->message_id;
$id = $message->from->id;
if($update->callback_query){
$id                                   = $update->callback_query->message->chat->id;
}else{
$id           						= $update->message->chat->id;
}
$user = $message->from->username;
$first = $message->from->first_name;
if(isset($update->callback_query)){
$chat_id = $update->callback_query->message->chat->id;
$message_id = $update->callback_query->message->message_id;
$data = $update->callback_query->data;
$user = $update->callback_query->from->username;
$first = $update->callback_query->from->first_name;
//التخزينات
$json = json_decode(file_get_contents('info.txt'),true);
$send = json_decode(file_get_contents('send.txt'),true);
}
function save($array){
file_put_contents('info.txt', json_encode($array));
}
function sends($array){
file_put_contents('send.txt', json_encode($array));
}
$json = json_decode(file_get_contents('info.txt'),1);
$send = json_decode(file_get_contents('send.txt'),1);
#countries
    $_co['country']['0'] = "روسيا 🇷🇺";
    $_co['country']['1'] = "أوكرانيا 🇺🇦";
    $_co['country']['2'] = "كازاخستان 🇰🇿";
    $_co['country']['3'] = "الصين 🇨🇳";
    $_co['country']['4'] = "الفلبين 🇵🇭";
    $_co['country']['5'] = "ميانمار 🇲🇲";
    $_co['country']['6'] = "إندونيسيا 🇮🇩";
    $_co['country']['7'] = "ماليزيا 🇲🇾";
    $_co['country']['8'] = "كينيا 🇰🇪";
    $_co['country']['9'] = "تنزانيا 🇹🇿";
    $_co['country']['10'] = "فيتنام 🇻🇳";
    $_co['country']['11'] = "قيرغيزستان 🇰🇬";
    $_co['country']['12'] = "إسرائيل 🇮🇱👞";
    $_co['country']['13'] = "هونغ كونغ 🇭🇰";
    $_co['country']['14'] = "بولندا 🇵🇱";
    $_co['country']['15'] = "🇬🇧 بريطانيا";
    $_co['country']['16'] = "مدغشقر 🇲🇬";
    $_co['country']['17'] = "نيجيريا 🇳🇬";
    $_co['country']['18'] = "ماكاو 🇲🇴";
    $_co['country']['19'] = "مصر 🇪🇬";
    $_co['country']['20'] = "الهند 🇮🇳";
    $_co['country']['21'] = "أيرلندا 🇮🇪";
    $_co['country']['22'] = "كمبوديا 🇰🇭";
    $_co['country']['23'] = "هايتي 🇭🇹";
    $_co['country']['24'] = "غامبيا 🇬🇲";
    $_co['country']['25'] = "صربيا 🇷🇸";
    $_co['country']['26'] = "اليمن 🇾🇪";
    $_co['country']['27'] = "جنوب إفريقيا 🇿🇦";
    $_co['country']['28'] = "رومانيا 🇷🇴";
    $_co['country']['29'] = "كولومبيا 🇨🇴";
    $_co['country']['30'] = "إستونيا 🇪🇪";
    $_co['country']['31'] = "أذربيجان 🇦🇿";
    $_co['country']['32'] = "كندا 🇨🇦";
    $_co['country']['33'] = "المغرب 🇲🇦";
    $_co['country']['34'] = "غانا 🇬🇭";
    $_co['country']['35'] = "الأرجنتين 🇦🇷";
    $_co['country']['36'] = "أوزبكستان 🇺🇿";
    $_co['country']['37'] = "الكاميرون 🇨🇲";
    $_co['country']['38'] = "تشاد 🇹🇩";
    $_co['country']['39'] = "المانيا 🇩🇪";
    $_co['country']['40'] = "ليتوانيا 🇱🇹";
    $_co['country']['41'] = "كرواتيا 🇭🇷";
    $_co['country']['42'] = "السويد 🇸🇪";
    $_co['country']['43'] = "العراق 🇮🇶";
    $_co['country']['44'] = "هولندا 🇳🇱";
    $_co['country']['45'] = "لاتيفيا 🇱🇻";
    $_co['country']['46'] = "النمسا 🇦🇹";
    $_co['country']['47'] = "بيلاروسيا 🇧🇾";
    $_co['country']['48'] = "تايلاند 🇹🇭";
    $_co['country']['49'] = "السعودية 🇸🇦";
    $_co['country']['50'] = "المكسيك 🇲🇽";
    $_co['country']['51'] = "تايوان 🇹🇼";
    $_co['country']['52'] = "اسبانيا 🇪🇸";
    $_co['country']['53'] = "إيران 🇮🇷";
    $_co['country']['54'] = "الجزائر 🇩🇿";
    $_co['country']['55'] = "سلوفينيا 🇸🇮";
    $_co['country']['56'] = "بنغلاديش 🇧🇩";
    $_co['country']['57'] = "السنغال 🇸🇳";
    $_co['country']['58'] = "تركيا 🇹🇷";
    $_co['country']['59'] = "التشيك 🇨🇿";
    $_co['country']['60'] = "سريلانكا 🇱🇰";
    $_co['country']['61'] = "بيرو 🇵🇪";
    $_co['country']['62'] = "باكستان 🇵🇰";
    $_co['country']['63'] = "نيوزيلندا 🇳🇿";
    $_co['country']['64'] = "غينيا 🇬🇳";
    $_co['country']['65'] = "مالي 🇲🇱";
    $_co['country']['66'] = "فنزويلا 🇻🇪";
    $_co['country']['67'] = "إثيوبيا 🇪🇹";
    $_co['country']['68'] = "منغوليا 🇲🇳";
    $_co['country']['69'] = "البرازيل 🇧🇷";
    $_co['country']['70'] = "أفغانستان 🇦🇫";
    $_co['country']['71'] = "أوغندا 🇺🇬";
    $_co['country']['72'] = "أنغولا 🇦🇴";
    $_co['country']['73'] = "قبرص 🇨🇾";
    $_co['country']['74'] = "فرنسا 🇫🇷";
    $_co['country']['75'] = "بابو 🇵🇬";
    $_co['country']['76'] = "موزمبيق 🇲🇿";
    $_co['country']['77'] = "نيبال 🇳🇵";
    $_co['country']['78'] = "بلجيكا 🇧🇪";
    $_co['country']['79'] = "بلغاريا 🇧🇬";
    $_co['country']['80'] = "مولدوفا 🇲🇩";
    $_co['country']['81'] = "إيطاليا 🇮🇹";
    $_co['country']['82'] = "باراغواي 🇵🇾";
    $_co['country']['83'] = "هندوراس 🇭🇳";
    $_co['country']['84'] = "تونس 🇹🇳";
    $_co['country']['85'] = "نيكاراغوا 🇳🇮";
    $_co['country']['86'] = "بوليفيا 🇧🇴";
    $_co['country']['87'] = "كوستاريكا 🇨🇷";
    $_co['country']['88'] = "غواتيمالا 🇬🇹";
    $_co['country']['89'] = "الإمارات 🇦🇪";
    $_co['country']['90'] = "زيمبابوي 🇿🇼";
    $_co['country']['91'] = "السودان 🇸🇩";
    $_co['country']['92'] = "الكويت 🇰🇼";
    $_co['country']['93'] = "سلفادور 🇸🇻";
    $_co['country']['94'] = "ليبيا 🇱🇾";
    $_co['country']['95'] = "جامايكا 🇯🇲";
    $_co['country']['96'] = "الاكوادور 🇪🇨";
    $_co['country']['97'] = "سوازيلاند 🇸🇿";
    $_co['country']['98'] = "عمان 🇴🇲";
    $_co['country']['99'] = "الدومينيكان 🇩🇴";
    $_co['country']['100'] = "سوريا 🍂";
    $_co['country']['101'] = "قطر 🇶🇦";
    $_co['country']['102'] = "بنما 🇵🇦";
    $_co['country']['103'] = "كوبا 🇨🇺";
    $_co['country']['104'] = "موريتانيا 🇲🇷";
    $_co['country']['105'] = "سيراليون 🇸🇱";
    $_co['country']['106'] = "الأردن 🇯🇴";
    $_co['country']['107'] = "البرتغال 🇵🇹";
    $_co['country']['108'] = "بربادوس 🇧🇧";
    $_co['country']['109'] = "بوروندي 🇧🇮";
    $_co['country']['110'] = "بنين 🇧🇯";
    $_co['country']['111'] = "جزر البهاما 🇧🇸";
    $_co['country']['112'] = "بوتسوانا 🇧🇼";
    $_co['country']['113'] = "بليز 🇧🇿";
    $_co['country']['114'] = "إفريقيا الوسطى 🇨🇫";
    $_co['country']['115'] = "دومينيكا 🇩🇲";
    $_co['country']['116'] = "غرينادا 🇬🇩";
    $_co['country']['117'] = "جورجيا 🇬🇪";
    $_co['country']['118'] = "اليونان 🇬🇷";
    $_co['country']['119'] = "غينيا بيساو 🇬🇼";
    $_co['country']['120'] = "غيانا 🇬🇾";
    $_co['country']['121'] = "جزر القمر 🇰🇲";
    $_co['country']['122'] = "ليبيريا 🇱🇷";
    $_co['country']['123'] = "ليسوتو 🇱🇸";
    $_co['country']['124'] = "ملاوي 🇲🇼";
    $_co['country']['125'] = "ناميبيا 🇳🇦";
    $_co['country']['126'] = "النيجر 🇳🇪";
    $_co['country']['127'] = "رواندا 🇷🇼";
    $_co['country']['128'] = "سلوفاكيا 🇸🇰";
    $_co['country']['129'] = "سورينام 🇸🇷";
    $_co['country']['130'] = "طاجيكستان 🇹🇯";
    $_co['country']['131'] = "موناكو 🇲🇨";
    $_co['country']['132'] = "البحرين 🇧🇭";
    $_co['country']['133'] = "زامبيا 🇿🇲";
    $_co['country']['134'] = "أرمينيا 🇦🇲";
    $_co['country']['135'] = "الصومال 🇸🇴";
    $_co['country']['136'] = "الكونغو 🇨🇬";
    $_co['country']['137'] = "تشيلي 🇨🇱";
    $_co['country']['138'] = "لبنان 🇱🇧";
    $_co['country']['139'] = "ألبانيا 🇦🇱";
    $_co['country']['140'] = "اوروغواي 🇺🇾";
    $_co['country']['141'] = "بوتان 🇧🇹";
    $_co['country']['142'] = "المالديف 🇲🇻";
    $_co['country']['143'] = "جوادلوب 🇬🇵";
    $_co['country']['144'] = "تركمانستان 🇹🇲";
    $_co['country']['145'] = "فنلندا 🇫🇮";
    $_co['country']['146'] = "لوسيا 🇱🇨";
    $_co['country']['147'] = "لوكسمبورغ 🇱🇺";
    $_co['country']['148'] = "جزر غرينادين 🇻🇨";
    $_co['country']['149'] = "غينيا الأستوائية 🇬🇶";
    $_co['country']['150'] = "جيبوتي 🇩🇯";
    $_co['country']['151'] = "جزر كايمان 🇰🇾";
    $_co['country']['152'] = "الجبل الأسود 🇲🇪";
    $_co['country']['153'] = "سويسرا 🇨🇭";
    $_co['country']['154'] = "النرويج 🇳🇴";
    $_co['country']['155'] = "استراليا 🇦🇺";
    $_co['country']['156'] = "إريتريا 🇪🇷";
    $_co['country']['157'] = "جنوب السودان 🇸🇸";
    $_co['country']['158'] = "اروبا 🇦🇼";
    $_co['country']['159'] = "أنغيلا 🇦🇮";
    $_co['country']['160'] = "اليابان 🇯🇵";
    $_co['country']['161'] = "شمال مقدونيا 🇲🇰";
    $_co['country']['162'] = "سيشيل 🇸🇨";
    $_co['country']['163'] = "كاليدونيا 🇳🇨";
    $_co['country']['164'] = "أمريكا 🇺🇸";
    $_co['country']['165'] = "فيجي 🇫🇯";
    $_co['country']['166'] = "كوريا الجنوبية 🇰🇷";
    $_co['country']['167'] = "برمودا 🇧🇲";
    $_co['country']['168'] = "الصحراء الغربية 🇪🇭";
#
#countries2
    $_co_o['country']['0'] = "RU";
    $_co_o['country']['1'] = "UA";
    $_co_o['country']['2'] = "KZ";
    $_co_o['country']['3'] = "CN";
    $_co_o['country']['4'] = "PH";
    $_co_o['country']['5'] = "MM";
    $_co_o['country']['6'] = "ID";
    $_co_o['country']['7'] = "MY";
    $_co_o['country']['8'] = "KE";
    $_co_o['country']['9'] = "TZ";
    $_co_o['country']['10'] = "VN";
    $_co_o['country']['11'] = "KG";
    $_co_o['country']['12'] = "IL";
    $_co_o['country']['13'] = "HK";
    $_co_o['country']['14'] = "PL";
    $_co_o['country']['15'] = "GB";
    $_co_o['country']['16'] = "MG";
    $_co_o['country']['17'] = "NG";
    $_co_o['country']['18'] = "MO";
    $_co_o['country']['19'] = "EG";
    $_co_o['country']['20'] = "IN";
    $_co_o['country']['21'] = "IE";
    $_co_o['country']['22'] = "KH";
    $_co_o['country']['23'] = "HT";
    $_co_o['country']['24'] = "GM";
    $_co_o['country']['25'] = "RS";
    $_co_o['country']['26'] = "YE";
    $_co_o['country']['27'] = "ZA";
    $_co_o['country']['28'] = "RO";
    $_co_o['country']['29'] = "CO";
    $_co_o['country']['30'] = "EE";
    $_co_o['country']['31'] = "AZ";
    $_co_o['country']['32'] = "CA";
    $_co_o['country']['33'] = "MA";
    $_co_o['country']['34'] = "GH";
    $_co_o['country']['35'] = "AR";
    $_co_o['country']['36'] = "UZ";
    $_co_o['country']['37'] = "CM";
    $_co_o['country']['38'] = "TD";
    $_co_o['country']['39'] = "DE";
    $_co_o['country']['40'] = "LT";
    $_co_o['country']['41'] = "HR";
    $_co_o['country']['42'] = "SE";
    $_co_o['country']['43'] = "IQ";
    $_co_o['country']['44'] = "NL";
    $_co_o['country']['45'] = "LV";
    $_co_o['country']['46'] = "AT";
    $_co_o['country']['47'] = "BY";
    $_co_o['country']['48'] = "TH";
    $_co_o['country']['49'] = "SA";
    $_co_o['country']['50'] = "MX";
    $_co_o['country']['51'] = "TW";
    $_co_o['country']['52'] = "ES";
    $_co_o['country']['53'] = "IR";
    $_co_o['country']['54'] = "DZ";
    $_co_o['country']['55'] = "SI";
    $_co_o['country']['56'] = "BD";
    $_co_o['country']['57'] = "SN";
    $_co_o['country']['58'] = "TR";
    $_co_o['country']['59'] = "CZ";
    $_co_o['country']['60'] = "LK";
    $_co_o['country']['61'] = "PE";
    $_co_o['country']['62'] = "PK";
    $_co_o['country']['63'] = "NZ";
    $_co_o['country']['64'] = "GQ";
    $_co_o['country']['65'] = "ML";
    $_co_o['country']['66'] = "VE";
    $_co_o['country']['67'] = "ET";
    $_co_o['country']['68'] = "MN";
    $_co_o['country']['69'] = "BR";
    $_co_o['country']['70'] = "AF";
    $_co_o['country']['71'] = "UG";
    $_co_o['country']['72'] = "AO";
    $_co_o['country']['73'] = "CY";
    $_co_o['country']['74'] = "FR";
    $_co_o['country']['75'] = "PG";
    $_co_o['country']['76'] = "MZ";
    $_co_o['country']['77'] = "NP";
    $_co_o['country']['78'] = "BE";
    $_co_o['country']['79'] = "BG";
    $_co_o['country']['80'] = "MD";
    $_co_o['country']['81'] = "IT";
    $_co_o['country']['82'] = "PY";
    $_co_o['country']['83'] = "HN";
    $_co_o['country']['84'] = "TN";
    $_co_o['country']['85'] = "NI";
    $_co_o['country']['86'] = "BO";
    $_co_o['country']['87'] = "CR";
    $_co_o['country']['88'] = "GT";
    $_co_o['country']['89'] = "AE";
    $_co_o['country']['90'] = "ZW";
    $_co_o['country']['91'] = "SD";
    $_co_o['country']['92'] = "KW";
    $_co_o['country']['93'] = "SV";
    $_co_o['country']['94'] = "LY";
    $_co_o['country']['95'] = "JM";
    $_co_o['country']['96'] = "EC";
    $_co_o['country']['97'] = "KW";
    $_co_o['country']['98'] = "OM";
    $_co_o['country']['99'] = "DO";
    $_co_o['country']['100'] = "SY";
    $_co_o['country']['101'] = "QA";
    $_co_o['country']['102'] = "PA";
    $_co_o['country']['103'] = "CU";
    $_co_o['country']['104'] = "MR";
    $_co_o['country']['105'] = "SL";
    $_co_o['country']['106'] = "JO";
    $_co_o['country']['107'] = "PT";
    $_co_o['country']['108'] = "BB";
    $_co_o['country']['109'] = "BI";
    $_co_o['country']['110'] = "BJ";
    $_co_o['country']['111'] = "BS";
    $_co_o['country']['112'] = "BW";
    $_co_o['country']['113'] = "BZ";
    $_co_o['country']['114'] = "CF";
    $_co_o['country']['115'] = "DM";
    $_co_o['country']['116'] = "GD";
    $_co_o['country']['117'] = "GE";
    $_co_o['country']['118'] = "GR";
    $_co_o['country']['119'] = "GW";
    $_co_o['country']['120'] = "GY";
    $_co_o['country']['121'] = "KM";
    $_co_o['country']['122'] = "LR";
    $_co_o['country']['123'] = "LS";
    $_co_o['country']['124'] = "MW";
    $_co_o['country']['125'] = "NA";
    $_co_o['country']['126'] = "NE";
    $_co_o['country']['127'] = "RW";
    $_co_o['country']['128'] = "SK";
    $_co_o['country']['129'] = "SR";
    $_co_o['country']['130'] = "TJ";
    $_co_o['country']['131'] = "MC";
    $_co_o['country']['132'] = "BH";
    $_co_o['country']['133'] = "ZM";
    $_co_o['country']['134'] = "AM";
    $_co_o['country']['135'] = "SO";
    $_co_o['country']['136'] = "CG";
    $_co_o['country']['137'] = "CL";
    $_co_o['country']['138'] = "LB";
    $_co_o['country']['139'] = "AL";
    $_co_o['country']['140'] = "UY";
    $_co_o['country']['141'] = "BT";
    $_co_o['country']['142'] = "MV";
    $_co_o['country']['143'] = "GP";
    $_co_o['country']['144'] = "TM";
    $_co_o['country']['145'] = "FI";
    $_co_o['country']['146'] = "LC";
    $_co_o['country']['147'] = "LU";
    $_co_o['country']['148'] = "VC";
    $_co_o['country']['149'] = "GQ";
    $_co_o['country']['150'] = "DJ";
    $_co_o['country']['151'] = "KY";
    $_co_o['country']['152'] = "ME";
    $_co_o['country']['153'] = "CH";
    $_co_o['country']['154'] = "NO";
    $_co_o['country']['155'] = "AU";
    $_co_o['country']['156'] = "ER";
    $_co_o['country']['157'] = "SS";
    $_co_o['country']['158'] = "AW";
    $_co_o['country']['159'] = "AI";
    $_co_o['country']['160'] = "JP";
    $_co_o['country']['161'] = "MK";
    $_co_o['country']['162'] = "SC";
    $_co_o['country']['163'] = "NC";
    $_co_o['country']['164'] = "US";
    $_co_o['country']['165'] = "FJ";
    $_co_o['country']['166'] = "KR";
    $_co_o['country']['167'] = "BM";
    $_co_o['country']['168'] = "EH";
#
//is not id
if(!in_array($id,$admin)){
if($text == "/start"){
bot("sendMessage",[
'chat_id'=>$id,
'text'=>"
.
",
"reply_to_message_id"=>$message_id,
]);
exit;
}
}

//is not admin
if(in_array($id,$admin)){
if($text == "/start" ){
bot("sendMessage",[
'chat_id'=>$id,
'text'=>"
مرحبا بك مطوري
تحكم اضافة الدول عبر الازرار بالاسفل 👇
",
"reply_to_message_id"=>$message_id,
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>"سحب يدوي 🔂",'callback_data'=>"numapp"]],
[['text'=>"اضافة دولة ☑️",'callback_data'=>"country"]],
[['text'=>"اضافة تطبيق ☑️",'callback_data'=>"addapp"]],
[['text'=>"حذف دولة 🚫",'callback_data'=>"dels"]],
[['text'=>"عرض الدول المضافة 💠",'callback_data'=>"soo"]],
[['text'=>"رفع ايبي الموقع 🗳",'callback_data'=>"apiget"]],
[['text'=>"ايقاف البوت وحذف ايبي الحساب",'callback_data'=>"apidel"]],
]
])
]);
unset($send[$chat_id]["mode"]);
sends($send);
exit;
}

//رجوع
if($data == "back"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
مرحبا بك مطوري
تحكم اضافة الدول عبر الازرار بالاسفل 👇
",
"reply_to_message_id"=>$message_id,
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>"سحب يدوي 🔂",'callback_data'=>"numapp"]],
[['text'=>"اضافة دولة ☑️",'callback_data'=>"country"]],
[['text'=>"اضافة تطبيق ☑️",'callback_data'=>"addapp"]],
[['text'=>"حذف دولة 🚫",'callback_data'=>"dels"]],
[['text'=>"عرض الدول المضافة 💠",'callback_data'=>"soo"]],
[['text'=>"رفع ايبي الموقع 🗳",'callback_data'=>"apiget"]],
[['text'=>"ايقاف البوت وحذف ايبي الحساب",'callback_data'=>"apidel"]],
]
])
]);
unset($send[$chat_id]["mode"]);
sends($send);
exit;
}

//رفع API
if($data == "apiget"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
📯 أرسل ايبي حسابك للموقع
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
$send[$chat_id]["mode"] = 'apiget';
sends($send);
exit;
}
if($text != "/start" && $text != null && $send[$chat_id]["mode"] == "apiget"){
bot("sendMessage",[
'chat_id'=>$id,
'text'=>"
تم رفع ايبي حسابك بنجاح 📬
",
"reply_to_message_id"=>$message_id,
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
file_put_contents("apifastpva.txt","$text");
unset($send[$chat_id]["mode"]);
sends($send);
exit;
}
if($data == "addapp"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
- ارسل رقم التطبيق بالموقع
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
$send[$chat_id]["mode"] = 'getapp';
sends($send);
exit;
}
if($text != "/start" && $text != null && $send[$chat_id]["mode"] == "getapp"){
bot("sendMessage",[
'chat_id'=>$id,
'text'=>"
تم رفع التطبيق الجديد $text بنجاح 📬
",
"reply_to_message_id"=>$message_id,
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
file_put_contents("app.txt","$text");
unset($send[$chat_id]["mode"]);
sends($send);
exit;
}
// حذف API
if($data == "apidel"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
❌ تم حذف ايبي حسابك للموقع من البوت
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
unlink("apifastpva.txt");
unset($send[$chat_id]["mode"]);
sends($send);
exit;
}

//إضافة دولة
if($data == "country"){
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
اختر إحدى الدول التي تريد اضافتها
لعرض باقي الدول أضغط على التالي ⏪
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'الدول','callback_data'=>"no thing"],['text'=>'الدول','callback_data'=>"no thing"]],
[['text'=>'روسيا 🇷🇺','callback_data'=>"addget-0"]],
[['text'=>'كازاخستان 🇰🇿','callback_data'=>"addget-2"],['text'=>'أوكرانيا 🇺🇦','callback_data'=>"addget-1"]],
[['text'=>'الفلبين 🇵🇭','callback_data'=>"addget-4"],['text'=>'الصين 🇨🇳','callback_data'=>"addget-3"]],
[['text'=>'إندونيسيا 🇮🇩','callback_data'=>"addget-6"],['text'=>'ميانمار 🇲🇲','callback_data'=>"addget-5"]],
[['text'=>'كينيا 🇰🇪','callback_data'=>"addget-8"],['text'=>'ماليزيا 🇲🇾','callback_data'=>"addget-7"]],
[['text'=>'فيتنام 🇻🇳','callback_data'=>"addget-10"],['text'=>'تنزانيا 🇹🇿','callback_data'=>"addget-9"]],
[['text'=>'إسرائيل 🇮🇱👞','callback_data'=>"addget-12"],['text'=>'قيرغيزستان 🇰🇬','callback_data'=>"addget-11"]],
[['text'=>'بولندا 🇵🇱','callback_data'=>"addget-14"],['text'=>'هونغ كونغ 🇭🇰','callback_data'=>"addget-13"]],
[['text'=>'مدغشقر 🇲🇬','callback_data'=>"addget-16"],['text'=>'🇬🇧 بريطانيا','callback_data'=>"addget-15"]],
[['text'=>'ماكاو 🇲🇴','callback_data'=>"addget-18"],['text'=>'نيجيريا 🇳🇬','callback_data'=>"addget-17"]],
[['text'=>'الهند 🇮🇳','callback_data'=>"addget-20"],['text'=>'مصر 🇪🇬','callback_data'=>"addget-19"]],
[['text'=>'كمبوديا 🇰🇭','callback_data'=>"addget-22"],['text'=>'أيرلندا 🇮🇪','callback_data'=>"addget-21"]],
[['text'=>'غامبيا 🇬🇲','callback_data'=>"addget-24"],['text'=>'هايتي 🇭🇹','callback_data'=>"addget-23"]],
[['text'=>'اليمن 🇾🇪','callback_data'=>"addget-26"],['text'=>'صربيا 🇷🇸','callback_data'=>"addget-25"]],
[['text'=>'رومانيا 🇷🇴','callback_data'=>"addget-28"],['text'=>'جنوب إفريقيا 🇿🇦','callback_data'=>"addget-27"]],
[['text'=>'إستونيا 🇪🇪','callback_data'=>"addget-30"],['text'=>'كولومبيا 🇨🇴','callback_data'=>"addget-29"]],
[['text'=>'كندا 🇨🇦','callback_data'=>"addget-32"],['text'=>'أذربيجان 🇦🇿','callback_data'=>"addget-31"]],
[['text'=>'غانا 🇬🇭','callback_data'=>"addget-34"],['text'=>'المغرب 🇲🇦','callback_data'=>"addget-33"]],
[['text'=>'أوزبكستان 🇺🇿','callback_data'=>"addget-36"],['text'=>'الأرجنتين 🇦🇷','callback_data'=>"addget-35"]],
[['text'=>'التالي ➡️','callback_data'=>"country_2"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}
if($data == "country_2"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
اختر إحدى الدول التي تريد اضافتها
لعرض باقي الدول أضغط على التالي ⏪
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'الدول','callback_data'=>"no thing"],['text'=>'الدول','callback_data'=>"no thing"]],
[['text'=>'تشاد 🇹🇩','callback_data'=>"addget-38"],['text'=>'الكاميرون 🇨🇲','callback_data'=>"addget-37"]],
[['text'=>'ليتوانيا 🇱🇹','callback_data'=>"addget-40"],['text'=>'المانيا 🇩🇪','callback_data'=>"addget-39"]],
[['text'=>'السويد 🇸🇪','callback_data'=>"addget-42"],['text'=>'كرواتيا 🇭🇷','callback_data'=>"addget-41"]],
[['text'=>'هولندا 🇳🇱','callback_data'=>"addget-44"],['text'=>'العراق 🇮🇶','callback_data'=>"addget-43"]],
[['text'=>'النمسا 🇦🇹','callback_data'=>"addget-46"],['text'=>'لاتيفيا 🇱🇻','callback_data'=>"addget-45"]],
[['text'=>'تايلاند 🇹🇭','callback_data'=>"addget-48"],['text'=>'بيلاروسيا 🇧🇾','callback_data'=>"addget-47"]],
[['text'=>'المكسيك 🇲🇽','callback_data'=>"addget-50"],['text'=>'السعودية 🇸🇦','callback_data'=>"addget-49"]],
[['text'=>'اسبانيا 🇪🇸','callback_data'=>"addget-52"],['text'=>'تايوان 🇹🇼','callback_data'=>"addget-51"]],
[['text'=>'الجزائر 🇩🇿','callback_data'=>"addget-54"],['text'=>'إيران 🇮🇷','callback_data'=>"addget-53"]],
[['text'=>'بنغلاديش 🇧🇩','callback_data'=>"addget-56"],['text'=>'سلوفينيا 🇸🇮','callback_data'=>"addget-55"]],
[['text'=>'تركيا 🇹🇷','callback_data'=>"addget-58"],['text'=>'السنغال 🇸🇳','callback_data'=>"addget-57"]],
[['text'=>'سريلانكا 🇱🇰','callback_data'=>"addget-60"],['text'=>'التشيك 🇨🇿','callback_data'=>"addget-59"]],
[['text'=>'باكستان 🇵🇰','callback_data'=>"addget-62"],['text'=>'بيرو 🇵🇪','callback_data'=>"addget-61"]],
[['text'=>'غينيا 🇬🇳','callback_data'=>"addget-64"],['text'=>'نيوزيلندا 🇳🇿','callback_data'=>"addget-63"]],
[['text'=>'فنزويلا 🇻🇪','callback_data'=>"addget-66"],['text'=>'مالي 🇲🇱','callback_data'=>"addget-65"]],
[['text'=>'منغوليا 🇲🇳','callback_data'=>"addget-68"],['text'=>'إثيوبيا 🇪🇹','callback_data'=>"addget-67"]],
[['text'=>'أفغانستان 🇦🇫','callback_data'=>"addget-70"],['text'=>'البرازيل 🇧🇷','callback_data'=>"addget-69"]],
[['text'=>'أنغولا 🇦🇴','callback_data'=>"addget-72"],['text'=>'أوغندا 🇺🇬','callback_data'=>"addget-71"]],
[['text'=>'فرنسا 🇫🇷','callback_data'=>"addget-74"],['text'=>'قبرص 🇨🇾','callback_data'=>"addget-73"]],
[['text'=>'السابق ⬅️','callback_data'=>"country"],['text'=>'التالي ➡️','callback_data'=>"country_3"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}
if($data == "country_3"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
اختر إحدى الدول التي تريد اضافتها
لعرض باقي الدول أضغط على التالي ⏪
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'الدول','callback_data'=>"no thing"],['text'=>'الدول','callback_data'=>"no thing"]],
[['text'=>'موزمبيق 🇲🇿','callback_data'=>"addget-76"],['text'=>'بابو 🇵🇬','callback_data'=>"addget-75"]],
[['text'=>'بلجيكا 🇧🇪','callback_data'=>"addget-78"],['text'=>'نيبال 🇳🇵','callback_data'=>"addget-77"]],
[['text'=>'مولدوفا 🇲🇩','callback_data'=>"addget-80"],['text'=>'بلغاريا 🇧🇬','callback_data'=>"addget-79"]],
[['text'=>'باراغواي 🇵🇾','callback_data'=>"addget-82"],['text'=>'إيطاليا 🇮🇹','callback_data'=>"addget-81"]],
[['text'=>'تونس 🇹🇳','callback_data'=>"addget-84"],['text'=>'هندوراس 🇭🇳','callback_data'=>"addget-83"]],
[['text'=>'بوليفيا 🇧🇴','callback_data'=>"addget-86"],['text'=>'نيكاراغوا 🇳🇮','callback_data'=>"addget-85"]],
[['text'=>'غواتيمالا 🇬🇹','callback_data'=>"addget-88"],['text'=>'كوستاريكا 🇨🇷','callback_data'=>"addget-87"]],
[['text'=>'زيمبابوي 🇿🇼','callback_data'=>"addget-90"],['text'=>'الإمارات 🇦🇪','callback_data'=>"addget-89"]],
[['text'=>'الكويت 🇰🇼','callback_data'=>"addget-92"],['text'=>'السودان 🇸🇩','callback_data'=>"addget-91"]],
[['text'=>'ليبيا 🇱🇾','callback_data'=>"addget-94"],['text'=>'سلفادور 🇸🇻','callback_data'=>"addget-93"]],
[['text'=>'الاكوادور 🇪🇨','callback_data'=>"addget-96"],['text'=>'جامايكا 🇯🇲','callback_data'=>"addget-95"]],
[['text'=>'عمان 🇴🇲','callback_data'=>"addget-98"],['text'=>'سوازيلاند 🇸🇿','callback_data'=>"addget-97"]],
[['text'=>'سوريا 🍂','callback_data'=>"addget-100"],['text'=>'الدومينيكان 🇩🇴','callback_data'=>"addget-99"]],
[['text'=>'بنما 🇵🇦','callback_data'=>"addget-102"],['text'=>'قطر 🇶🇦','callback_data'=>"addget-101"]],
[['text'=>'موريتانيا 🇲🇷','callback_data'=>"addget-104"],['text'=>'كوبا 🇨🇺','callback_data'=>"addget-103"]],
[['text'=>'الأردن 🇯🇴','callback_data'=>"addget-106"],['text'=>'سيراليون 🇸🇱','callback_data'=>"addget-105"]],
[['text'=>'بربادوس 🇧🇧','callback_data'=>"addget-108"],['text'=>'البرتغال 🇵🇹','callback_data'=>"addget-107"]],
[['text'=>'بنين 🇧🇯','callback_data'=>"addget-110"],['text'=>'بوروندي 🇧🇮','callback_data'=>"addget-109"]],
[['text'=>'بوتسوانا 🇧🇼','callback_data'=>"addget-112"],['text'=>'جزر البهاما 🇧🇸','callback_data'=>"addget-111"]],
[['text'=>'إفريقيا الوسطى 🇨🇫','callback_data'=>"addget-114"],['text'=>'بليز 🇧🇿','callback_data'=>"addget-113"]],
[['text'=>'السابق ⬅️','callback_data'=>"country_2"],['text'=>'التالي ➡️','callback_data'=>"country_4"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}
if($data == "country_4"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
اختر إحدى الدول التي تريد اضافتها
لعرض باقي الدول أضغط على التالي ⏪
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'الدول','callback_data'=>"no thing"],['text'=>'الدول','callback_data'=>"no thing"]],
[['text'=>'غرينادا 🇬🇩','callback_data'=>"addget-116"],['text'=>'دومينيكا 🇩🇲','callback_data'=>"addget-115"]],
[['text'=>'اليونان 🇬🇷','callback_data'=>"addget-118"],['text'=>'جورجيا 🇬🇪','callback_data'=>"addget-117"]],
[['text'=>'غيانا 🇬🇾','callback_data'=>"addget-120"],['text'=>'غينيا بيساو 🇬🇼','callback_data'=>"addget-119"]],
[['text'=>'ليبيريا 🇱🇷','callback_data'=>"addget-122"],['text'=>'جزر القمر 🇰🇲','callback_data'=>"addget-121"]],
[['text'=>'ملاوي 🇲🇼','callback_data'=>"addget-124"],['text'=>'ليسوتو 🇱🇸','callback_data'=>"addget-123"]],
[['text'=>'النيجر 🇳🇪','callback_data'=>"addget-126"],['text'=>'ناميبيا 🇳🇦','callback_data'=>"addget-125"]],
[['text'=>'سلوفاكيا 🇸🇰','callback_data'=>"addget-128"],['text'=>'رواندا 🇷🇼','callback_data'=>"addget-127"]],
[['text'=>'طاجيكستان 🇹🇯','callback_data'=>"addget-130"],['text'=>'سورينام 🇸🇷','callback_data'=>"addget-129"]],
[['text'=>'البحرين 🇧🇭','callback_data'=>"addget-132"],['text'=>'موناكو 🇲🇨','callback_data'=>"addget-131"]],
[['text'=>'أرمينيا 🇦🇲','callback_data'=>"addget-134"],['text'=>'زامبيا 🇿🇲','callback_data'=>"addget-133"]],
[['text'=>'الكونغو 🇨🇬','callback_data'=>"addget-136"],['text'=>'الصومال 🇸🇴','callback_data'=>"addget-135"]],
[['text'=>'لبنان 🇱🇧','callback_data'=>"addget-138"],['text'=>'تشيلي 🇨🇱','callback_data'=>"addget-137"]],
[['text'=>'اوروغواي 🇺🇾','callback_data'=>"addget-140"],['text'=>'ألبانيا 🇦🇱','callback_data'=>"addget-139"]],
[['text'=>'المالديف 🇲🇻','callback_data'=>"addget-142"],['text'=>'بوتان 🇧🇹','callback_data'=>"addget-141"]],
[['text'=>'تركمانستان 🇹🇲','callback_data'=>"addget-144"],['text'=>'جوادلوب 🇬🇵','callback_data'=>"addget-143"]],
[['text'=>'لوسيا 🇱🇨','callback_data'=>"addget-146"],['text'=>'فنلندا 🇫🇮','callback_data'=>"addget-145"]],
[['text'=>'جزر غرينادين 🇻🇨','callback_data'=>"addget-148"],['text'=>'لوكسمبورغ 🇱🇺','callback_data'=>"addget-147"]],
[['text'=>'جيبوتي 🇩🇯','callback_data'=>"addget-150"],['text'=>'غينيا الأستوائية 🇬🇶','callback_data'=>"addget-149"]],
[['text'=>'الجبل الأسود 🇲🇪','callback_data'=>"addget-152"],['text'=>'جزر كايمان 🇰🇾','callback_data'=>"addget-151"]],
[['text'=>'السابق ⬅️','callback_data'=>"country_3"],['text'=>'التالي ➡️','callback_data'=>"country_5"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}
if($data == "country_5"){
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
اختر إحدى الدول التي تريد اضافتها
لعرض باقي الدول أضغط على التالي ⏪
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'الدول','callback_data'=>"no thing"],['text'=>'الدول','callback_data'=>"no thing"]],
[['text'=>'النرويج 🇳🇴','callback_data'=>"addget-154"],['text'=>'سويسرا 🇨🇭','callback_data'=>"addget-153"]],
[['text'=>'إريتريا 🇪🇷','callback_data'=>"addget-156"],['text'=>'استراليا 🇦🇺','callback_data'=>"addget-155"]],
[['text'=>'اروبا 🇦🇼','callback_data'=>"addget-158"],['text'=>'جنوب السودان 🇸🇸','callback_data'=>"addget-157"]],
[['text'=>'اليابان 🇯🇵','callback_data'=>"addget-160"],['text'=>'أنغيلا 🇦🇮','callback_data'=>"addget-159"]],
[['text'=>'سيشيل 🇸🇨','callback_data'=>"addget-162"],['text'=>'شمال مقدونيا 🇲🇰','callback_data'=>"addget-161"]],
[['text'=>'أمريكا 🇺🇸','callback_data'=>"addget-164"],['text'=>'كاليدونيا 🇳🇨','callback_data'=>"addget-163"]],
[['text'=>'كوريا الجنوبية 🇰🇷','callback_data'=>"addget-166"],['text'=>'فيجي 🇫🇯','callback_data'=>"addget-165"]],
[['text'=>'الصحراء الغربية 🇪🇭','callback_data'=>"addget-168"],['text'=>'برمودا 🇧🇲','callback_data'=>"addget-167"]],
[['text'=>'السابق ⬅️','callback_data'=>"country_4"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}

if(strpos($data,"addget")!== false){
$ex = explode("-", $data);
$co = $ex[1];
$country = $_co_o['country'][$co];
$name = $_co['country'][$co];
foreach($json as $cont => $key){
if($country == $cont){
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>'⚠️ ⁞ عذرا عزيزي قد قمت ب إضافة هذه الدولة من قبل ♻️',
'show_alert'=>true
]);
exit;
}
}
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>'تم تنفيذ طلبك 👍',
'show_alert'=>false
]);
bot('EditMessageText',[
'chat_id'=>$id,
'message_id'=>$message_id,
'text'=>"
✅ تم إضافة الدولة بنجاح
",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
$json[$country] = $co;
save($json);
file_put_contents("info.txt",json_encode($json));
exit;
}

//حذف الدول
if($data == "dels"){
if(count($json) >= 1){
$keyboard     = [];
$keyboard['inline_keyboard'][] = [['text'=>'رمز الدولة','callback_data'=>'on'],['text'=>'الدولة','callback_data'=>'on']];
foreach($json as $cont => $key){
$name = $_co['country'][$key];
$keyboard['inline_keyboard'][] = [['text'=>"$key",'callback_data'=>"contdel-$cont-$key"],['text'=>"$name",'callback_data'=>"contdel-$cont-$key"]];
}
$keyboard['inline_keyboard'][] = [['text'=>'رجوع','callback_data'=>"back"]];
$keyboad      = json_encode($keyboard);
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
⚙ إضغط على الدولة الذي تريد حذفها من قائمة الصيد ⬇️
",
'parse_mode'=>"MarkDown",
'reply_markup'=>($keyboad),
]);
exit;
}else{
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>'🚫 عذرا لم تقم ب إضافة أي دولة للصيد بعد',
'show_alert'=>true
]);
exit;
}
}

if(strpos($data,"contdel")!== false){
$ex = explode("-", $data);
$country = $ex[1];
$key = $ex[2];
$name = $_co['country'][$key];
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
🚫 تم حذف الدولة بنجاح
",
'parse_mode'=>"MarkDown",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
unset($json[$country]);
save($json);
file_put_contents("info.txt",json_encode($json));
exit;
}
}

//عرض الدول
if($data == "soo"){
if(count($json) >= 1){
$keyboard     = [];
$keyboard['inline_keyboard'][] = [['text'=>'رمز الدولة','callback_data'=>'on'],['text'=>'الدولة','callback_data'=>'on']];
foreach($json as $cont=>$key){
$name = $_co['country'][$key];
$keyboard['inline_keyboard'][] = [['text'=>"$key",'callback_data'=>"no-$key"],['text'=>"$name",'callback_data'=>"no-$key"]];
}
$keyboard['inline_keyboard'][] = [['text'=>'رجوع','callback_data'=>"back"]];
$keyboad      = json_encode($keyboard);
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
♻️ هذه جميع الدول التي قمت ب إضافتها إلى قائمة الصيد ⬇️
",
'parse_mode'=>"MarkDown",
'reply_markup'=>($keyboad),
]);
exit;
}else{
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>'🚫 عذرا لم تقم ب إضافة أي دولة للصيد بعد',
'show_alert'=>true
]);
exit;
}
}

// سحب يدوي
if($data == "numapp"){
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
- قم بالضغط على الدولة لسحب الرقم.
",
'parse_mode'=>"MarkDown",
'reply_markup'=>json_encode([
'inline_keyboard'=>[
[['text'=>'السعودية 🇸🇦','callback_data'=>"Ai|SA"]],
[['text'=>'اليمن 🇾🇪','callback_data'=>"Ai|YE"]],
[['text'=>'الإمارات 🇦🇪','callback_data'=>"Ai|AE"]],
[['text'=>'قطر 🇶🇦','callback_data'=>"Ai|QA"]],
[['text'=>'ليبيا 🇱🇾','callback_data'=>"Ai|LY"]],
[['text'=>'مصر 🇪🇬','callback_data'=>"Ai|EG"]],
[['text'=>'العراق 🇮🇶','callback_data'=>"Ai|IQ"]],
[['text'=>'سوريا 🇸🇾','callback_data'=>"Ai|SY"]],
[['text'=>'تونس 🇹🇳','callback_data'=>"Ai|TN"]],
[['text'=>'الجزائر 🇩🇿','callback_data'=>"Ai|DZ"]],
[['text'=>'تركيا 🇹🇷','callback_data'=>"Ai|TR"]],
[['text'=>'رجوع','callback_data'=>"back"]]
]
])
]);
exit;
}
if(strpos($data,"Ai")!== false){
$exdata = explode("|",$data);
$key = $exdata[1];
$fali = array("No user found.","Invalid Service ID","Invalid country ID","Invalid channel ID","Not available for this channel.","The phone number is not available. Please try again later. Suggestion: Try another country or another channel");
$api = json_decode(file_get_contents("http://api.fastpva.com/pvapublic/sms/getNumber?myPid=3543&apikey=$API_SU&locale=$key"),1);
$idnumber = $api->data->orderId;
$num = $api->data->number;

if($num == null ){
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>"- ليس متوفر....",
'show_alert'=>true,
]);
return false;
}
bot("sendMessage",[
'chat_id'=>$chat_id,
'text'=>"
wa.me/$num
`$num`
*$idnumber*
",
'parse_mode'=>"MarkDown",
'reply_markup' => json_encode([
'inline_keyboard' => [
[['text' => "✳️ ⁞ تحديث.", 'callback_data' => "get|$num|$idnumber"]],
[['text' => "⚠️ ⁞ إلغاء الرقم.", 'callback_data' => "del|$num|$idnumber"]],
]
])
]);
exit;
}

//طلب كود الرقم
if(strpos($data,"get")!== false){
$exdata = explode("|",$data);
$num = $exdata[1];
$idnumber = $exdata[2];
$Link = json_decode(file_get_contents("http://api.fastpva.com/pvapublic/sms/getCode?orderId=$idnumber&apikey=$API_SU"));
$code = $Link->data->code;
//$code    = str_replace('-','',$code);
if($code == null){
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>"🚫 لم يصل الكود",
'show_alert'=>true,
]);
return false;
}
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
تم وصول الكود بنجاح

*number*: `$num`
*code*: `$code`
",
'parse_mode'=>"MarkDown",
]);
exit;
}

//حضر الرقم
if(strpos($data,"del")!== false){
$exdata = explode("|",$data);
$num = $exdata[1];
$nums    = str_replace('+','',$num);
$idnumber = $exdata[2];
$get = json_decode(file_get_contents("http://api.fastpva.com/pvapublic/sms/releaseNumber?orderId=$idnumber&apikey=$API_SU"));
$Link = json_decode(file_get_contents("http://api.fastpva.com/pvapublic/sms/getCode?orderId=$idnumber&apikey=$API_SU"));
$code = $Link->data->code;
//$code    = str_replace('-','',$code);
if($code != null){
bot('answercallbackquery',[
'callback_query_id' => $update->callback_query->id,
'text'=>"الكود قد تم جلبة",
'show_alert'=>true,
]);
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
 تم وصول الكود بنجاح.
الرقم: `$num`
الكود: `$code`
",
'parse_mode'=>"MarkDown",
]);
exit;
}
bot('EditMessageText',[
'chat_id'=>$chat_id,
'message_id'=>$message_id,
'text'=>"
تم حظر الرقم بنجاح.
",
]);
exit;
}


















