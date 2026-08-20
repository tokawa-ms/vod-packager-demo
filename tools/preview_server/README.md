# Preview server

生成済み HLS package を localhost に mount し、Plyr と hls.js で
multi-bitrate 再生を確認するための独立した test tool です。
`vod-packager` package の module や dependency には含まれません。

```powershell
python .\tools\preview_server\server.py .\output\<GUID> --open-browser
```

既定の URL は `http://localhost:8000/` です。別の port を使用する場合は
`--port 8080` を指定します。Server は `127.0.0.1` のみに bind されます。
Plyr と hls.js は jsDelivr から取得するため、page の初回表示には internet
接続が必要です。`Ctrl+C` で server を終了できます。

Player の下には、横軸を動画の再生時間、縦軸を選択 bitrate とした graph が
表示されます。水色の線は hls.js が実際に選択した rendition、水平線は
package 内の bitrate ladder を表します。Chrome/Edge DevTools の Network
throttling を再生中に変更すると、ABR による上下動を demo できます。
回線変更への反応を見せやすくするため、forward buffer は既定の 30 秒ではなく
約 2 segments（12 秒）に制限し、VoD の bandwidth 推定も短い sampling window
を使用します。画面右下の `Buffer` badge で現在の先読み秒数を確認できます。

Test:

```powershell
python -m unittest discover -s .\tools\preview_server\tests -v
```

次の項目を検証します。

- Player page、HLS manifest、streaming file の配信と MIME type
- Mount 対象外および directory traversal access の拒否
- `master.m3u8` を含む package directory の入力検証
- Seek 時の bitrate graph sample reset と 2 segment buffer/ABR 設定
- Segment download 中断時の想定内 client disconnect 処理

この test suite は `src\vod_packager` の package tests とは独立しています。
