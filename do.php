<?php

include("config.php");
//key


//fun
function curl($url){ 
  $ch = curl_init(); 
  curl_setopt($ch,CURLOPT_URL,$url); 
  curl_setopt($ch,CURLOPT_RETURNTRANSFER,true); 
  $res = curl_exec($ch); 
  return $res; 
}

//var
$get = file_get_contents("info.txt");
$getjson = json_decode($get);

$fali = array("Please try again later","Please try again later.");

//loop
if($get != null){
  foreach ($getjson as $cont => $key){

for($i=0;$i<150;$i++){

    $check = curl("https://api.fastpva.com/pvapublic/sms/getNumber?myPid=$API_APP&apikey=$API_SU&locale=$cont");

     // $b = http_build_query($data);
      //curl("https://api.telegram.org/bot".$token."/sendmessage?$b");
   
$ex = explode('"',$check);
$no=$ex[5];
if(in_array($no,$fali)){
echo "$i -".$check."<br>";
continue;
}else {
echo $check;

$ex = explode('"',$check);
$num = $ex[5];
if($num != null){
$ex = explode('"',$check);
$num = $ex[7];
$idnumber=$ex[11];
if($num != null or $idnumber != null){
$tex = "
t.me/$num
`$num`
*$idnumber*
";
}
$data =array(
'chat_id'=>$me,
'text'=>"
$tex
",
'parse_mode'=>"MarkDown",
'reply_markup' => json_encode([
'inline_keyboard' => [
[['text' => "✳️ ⁞ تحديث.", 'callback_data' => "get|$num|$idnumber"]],
[['text' => "⚠️ ⁞ إلغاء الرقم.", 'callback_data' => "del|$num|$idnumber"]],
]])
        );
        
      $b = http_build_query($data);
      echo curl("https://api.telegram.org/bot".$token."/sendmessage?$b");}
    }
    
  }
}
}


?>
