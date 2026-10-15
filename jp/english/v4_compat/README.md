How the Android 14 build (Versions/4) was made, 2026-09-25. Base = Versions/3 (toxin-icons).
1. apktool 3.0.1:  apktool d -r -o dec <base.apk>   (-r leaves resources raw)
2. In dec/smali/com/capcom/zombiecafeandroidJP/{ZombieCafeAndroid,m}.smali replace each
     invoke-virtual {vX}, Landroid/telephony/TelephonyManager;->getDeviceId|getSimSerialNumber()Ljava/lang/String;
     move-result-object vY
   with   const-string vY, "000000000000000"      (9 sites)
3. apktool b dec -o tmp.apk ; take ONLY classes.dex from tmp.apk
4. python3 axml_target.py AndroidManifest.xml AndroidManifest.patched.xml 24   (one-byte targetSdk patch)
5. Copy every entry of the base APK except META-INF/*, swapping in the new classes.dex + manifest
   (keep each entry's compression), then:
     zipalign -p -f 4 unsigned.apk aligned.apk
     apksigner sign --ks <repo>/debug.keystore --ks-key-alias alias_name --ks-pass pass:zombiecafe --out out.apk aligned.apk
6. python3 zipdiff.py <original.apk> out.apk   -> lists every changed file
