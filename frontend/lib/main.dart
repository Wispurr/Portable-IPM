import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

enum PageType { home, map, settings }

// ===== 數據顯示模組（可用假資料 / 可接 WebSocket）=====
class _SensorData {
  final double offsetDeg;
  final double? mainDistanceM;
  final List<String> warnings;

  _SensorData({
    required this.offsetDeg,
    required this.mainDistanceM,
    required this.warnings,
  });

  // 從 top-level JSON 取 data.offset / data.obstacles / data.warnings
  factory _SensorData.fromTopLevelJson(Map<String, dynamic> j) {
    final data = (j['data'] as Map?) ?? {};
    // 代表距離：從 obstacles 取最小 distance
    double? mainDist;
    final rawObs = data['obstacles'];
    if (rawObs is List && rawObs.isNotEmpty) {
      final distances = rawObs
          .whereType<Map>()
          .map(
            (m) => (m['distance'] is num)
                ? (m['distance'] as num).toDouble()
                : (m['distance'] is String)
                ? double.tryParse(m['distance']) ?? double.infinity
                : double.infinity,
          )
          .toList();
      if (distances.isNotEmpty) {
        distances.sort();
        mainDist = distances.first.isFinite ? distances.first : null;
      }
    }
    final warns = (data['warnings'] is List)
        ? (data['warnings'] as List).whereType<String>().toList()
        : <String>[];

    final off = data['offset'];
    final offset = (off is num)
        ? off.toDouble()
        : (off is String)
        ? double.tryParse(off) ?? 0.0
        : 0.0;

    return _SensorData(
      offsetDeg: offset,
      mainDistanceM: mainDist,
      warnings: warns,
    );
  }
}

class DataDisplayPanel extends StatefulWidget {
  /// 圖片 WebSocket URL
  final String? wsUrl;

  /// 數據 WebSocket URL
  final String? dataUrl;

  /// 是否使用假資料
  final bool useFake;

  /// 門檻值（預設值，可能被 dataUrl 的資料覆蓋）
  final double angleWarnDeg;
  final double minDistM;
  final double maxDistM;

  const DataDisplayPanel({
    super.key,
    this.wsUrl,
    this.dataUrl,
    this.useFake = false,
    this.angleWarnDeg = 5.0,
    this.minDistM = 0.8,
    this.maxDistM = 2.0,
  });

  @override
  State<DataDisplayPanel> createState() => _DataDisplayPanelState();
}

class _DataDisplayPanelState extends State<DataDisplayPanel> {
  // 現有的圖片資料相關
  StreamSubscription? _imageSub;
  WebSocketChannel? _imageChannel;

  // 新增：感測器資料相關
  StreamSubscription? _dataSub;
  WebSocketChannel? _dataChannel;

  _SensorData? _last;
  Timer? _fakeTimer;
  bool _connected = false;

  // 動態門檻值（會被 dataUrl 更新）
  double _currentAngleWarnDeg;
  double _currentMinDistM;
  double _currentMaxDistM;

  bool _disposed = false;
  bool _isConnecting = false;

  _DataDisplayPanelState()
    : _currentAngleWarnDeg = 5.0,
      _currentMinDistM = 0.8,
      _currentMaxDistM = 2.0;

  @override
  void initState() {
    super.initState();

    _currentAngleWarnDeg = widget.angleWarnDeg;
    _currentMinDistM = widget.minDistM;
    _currentMaxDistM = widget.maxDistM;

    if (widget.useFake) {
      _startFakeData();
    } else {
      if (widget.dataUrl != null) {
        _connectDataWebSocket();
      }
    }
  }

  void _startFakeData() {
    if (_disposed) return;

    _fakeTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_disposed || !mounted) {
        t.cancel();
        return;
      }

      final fakeJson = {
        "timestamp": DateTime.now().toIso8601String(),
        "status": "success",
        "data": {
          "offset": (t.tick % 10 - 5) * 0.8,
          "obstacles": [
            {"distance": 0.9 + 0.6 * ((t.tick % 7) / 7), "angle": 10},
            {"distance": 1.2 + 0.4 * ((t.tick % 5) / 5), "angle": -8},
          ],
          "warnings": (t.tick % 6 == 0) ? ["距離過近"] : [],
        },
      };

      if (t.tick % 8 == 0 && mounted) {
        setState(() {
          _currentAngleWarnDeg = 4.0 + (t.tick % 3);
          _currentMinDistM = 0.7 + (t.tick % 2) * 0.1;
          _currentMaxDistM = 1.8 + (t.tick % 3) * 0.2;
        });
      }

      if (mounted) {
        setState(() {
          _connected = true;
          _last = _SensorData.fromTopLevelJson(
            fakeJson.cast<String, dynamic>(),
          );
        });
      }
    });
  }

  void _connectDataWebSocket() {
    if (_isConnecting || _disposed) return;

    _isConnecting = true;

    try {
      _dataChannel?.sink.close();
      _dataSub?.cancel();

      _dataChannel = WebSocketChannel.connect(Uri.parse(widget.dataUrl!));
      _dataSub = _dataChannel!.stream.listen(
        (event) {
          if (_disposed || !mounted) return;

          if (event is String) {
            try {
              final map = jsonDecode(event);
              if (map is Map<String, dynamic>) {
                _handleDataMessage(map);
              }
            } catch (e) {
              print('解析資料 WebSocket 訊息失敗: $e');
            }
          }
        },
        onDone: () {
          if (!_disposed && mounted) {
            setState(() => _connected = false);
            _scheduleDataReconnect();
          }
        },
        onError: (e) {
          print('Data WebSocket error: $e');
          if (!_disposed && mounted) {
            setState(() => _connected = false);
            _scheduleDataReconnect();
          }
        },
      );

      if (mounted) {
        setState(() => _connected = true);
      }
    } catch (e) {
      print('Data connection failed: $e');
      if (!_disposed && mounted) {
        setState(() => _connected = false);
        _scheduleDataReconnect();
      }
    } finally {
      _isConnecting = false;
    }
  }

  void _handleDataMessage(Map<String, dynamic> data) {
    if (_disposed || !mounted) return;

    setState(() {
      if (data.containsKey('data')) {
        _last = _SensorData.fromTopLevelJson(data);
      }

      if (data.containsKey('thresholds')) {
        final thresholds = data['thresholds'] as Map?;
        if (thresholds != null) {
          if (thresholds['angleWarnDeg'] is num) {
            _currentAngleWarnDeg = (thresholds['angleWarnDeg'] as num)
                .toDouble();
          }
          if (thresholds['minDistM'] is num) {
            _currentMinDistM = (thresholds['minDistM'] as num).toDouble();
          }
          if (thresholds['maxDistM'] is num) {
            _currentMaxDistM = (thresholds['maxDistM'] as num).toDouble();
          }
        }
      }

      if (data['angleWarnDeg'] is num) {
        _currentAngleWarnDeg = (data['angleWarnDeg'] as num).toDouble();
      }
      if (data['minDistM'] is num) {
        _currentMinDistM = (data['minDistM'] as num).toDouble();
      }
      if (data['maxDistM'] is num) {
        _currentMaxDistM = (data['maxDistM'] as num).toDouble();
      }
    });
  }

  void _scheduleDataReconnect() {
    if (_disposed) return;

    Timer(const Duration(seconds: 5), () {
      if (!_disposed && mounted) {
        _connectDataWebSocket();
      }
    });
  }

  @override
  void dispose() {
    _disposed = true;
    _fakeTimer?.cancel();
    _imageSub?.cancel();
    _dataSub?.cancel();

    try {
      _imageChannel?.sink.close();
      _dataChannel?.sink.close();
    } catch (e) {
      print('Close channels failed: $e');
    }

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = _last;
    final angleBad = d != null && d.offsetDeg.abs() > _currentAngleWarnDeg;
    final tooClose =
        d?.mainDistanceM != null && d!.mainDistanceM! < _currentMinDistM;
    final tooFar =
        d?.mainDistanceM != null && d!.mainDistanceM! > _currentMaxDistM;
    final hasWarn =
        angleBad || tooClose || tooFar || (d?.warnings.isNotEmpty ?? false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 連線狀態
        Row(
          children: [
            Icon(
              _connected ? Icons.cloud_done : Icons.cloud_off,
              size: 18,
              color: _connected ? Colors.green : Colors.grey,
            ),
            const SizedBox(width: 6),
            Text(
              _connected ? '已連線' : '未連線',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const Spacer(),
            // 顯示當前門檻值
            Text(
              '門檻: ${_currentAngleWarnDeg.toStringAsFixed(1)}° / ${_currentMinDistM.toStringAsFixed(1)}-${_currentMaxDistM.toStringAsFixed(1)}m',
              style: const TextStyle(fontSize: 10, color: Colors.grey),
            ),
          ],
        ),
        const SizedBox(height: 6),

        // 使用 Visibility 取代 collection-if
        Visibility(
          visible: hasWarn,
          child: Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_composeWarning(d, angleBad, tooClose, tooFar)),
                  ),
                ],
              ),
            ),
          ),
        ),

        Row(
          children: [
            Expanded(
              child: _metricCard(
                title: '偏移角度',
                value: d == null ? '--' : '${d.offsetDeg.toStringAsFixed(1)}°',
                icon: Icons.navigation,
                danger: angleBad,
                subtitle: '門檻 ±${_currentAngleWarnDeg.toStringAsFixed(1)}°',
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _metricCard(
                title: '最近距離',
                value: d?.mainDistanceM == null
                    ? '--'
                    : '${d!.mainDistanceM!.toStringAsFixed(2)} m',
                icon: Icons.straighten,
                danger: tooClose || tooFar,
                subtitle:
                    '允許 ${_currentMinDistM.toStringAsFixed(1)}-${_currentMaxDistM.toStringAsFixed(1)} m',
              ),
            ),
          ],
        ),
      ],
    );
  }

  String _composeWarning(
    _SensorData? d,
    bool angleBad,
    bool tooClose,
    bool tooFar,
  ) {
    final msgs = <String>[];
    if (angleBad)
      msgs.add('偏移過大（>${_currentAngleWarnDeg.toStringAsFixed(1)}°）');
    if (tooClose) msgs.add('距離過近（<${_currentMinDistM.toStringAsFixed(1)}m）');
    if (tooFar) msgs.add('距離過遠（>${_currentMaxDistM.toStringAsFixed(1)}m）');
    if (d != null && d.warnings.isNotEmpty) msgs.addAll(d.warnings);
    return msgs.isEmpty ? '—' : msgs.join(' ・ ');
  }

  Widget _metricCard({
    required String title,
    required String value,
    required IconData icon,
    required bool danger,
    String? subtitle,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(icon, size: 24, color: danger ? Colors.red : null),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 13, color: Colors.grey),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: danger ? Colors.red : null,
                    ),
                  ),
                  // 用 Visibility 取代 collection-if + spread
                  Visibility(
                    visible: subtitle != null,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(
                          subtitle ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: MainLayout(),
    );
  }
}

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});
  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  PageType selectedPage = PageType.home;
  bool isSidebarOpen = true;

  Widget _buildPage() {
    switch (selectedPage) {
      case PageType.map:
        return const MapPage();
      case PageType.settings:
        return const SettingsPage();
      case PageType.home:
      default:
        return const HomePage();
    }
  }

  Widget _btn(String label, PageType page) {
    final isSel = selectedPage == page;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: ElevatedButton(
        onPressed: () => setState(() => selectedPage = page),
        style: ElevatedButton.styleFrom(
          backgroundColor: isSel ? const Color(0xFF7DB196) : Colors.white,
          foregroundColor: Colors.black,
          minimumSize: const Size(80, 55),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: isSidebarOpen ? 120 : 60,
            color: const Color(0xFFC0C0C0),
            child: Column(
              children: [
                const SizedBox(height: 20),
                IconButton(
                  icon: const Icon(Icons.menu),
                  onPressed: () =>
                      setState(() => isSidebarOpen = !isSidebarOpen),
                ),
                // explicit widget instead of collection-if + spread
                Visibility(
                  visible: isSidebarOpen,
                  child: Column(
                    children: [
                      _btn("首頁", PageType.home),
                      _btn("地圖", PageType.map),
                      _btn("設定", PageType.settings),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(child: _buildPage()),
        ],
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final String wsUrl = "ws://127.0.0.1:8080/stream/ws/image";

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;

  String _status = 'disconnected';
  Uint8List? _lastImage;
  int _frames = 0;
  int _fps = 0;
  Timer? _fpsTimer;

  @override
  void initState() {
    super.initState();
    _fpsTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() {
        _fps = _frames;
        _frames = 0;
      });
    });
    _connectWs();
  }

  @override
  void dispose() {
    _fpsTimer?.cancel();
    _cancelAll();
    super.dispose();
  }

  // 修改 _HomePageState 中的 _connectWs 方法

  void _connectWs() {
    _cancelAll();
    setState(() {
      _status = 'connecting';
      _lastImage = null;
    });

    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _sub = _channel!.stream.listen(
        (event) {
          if (event is String) {
            // 檢查是否為 base64 圖片資料
            try {
              // 嘗試解碼 base64
              final bytes = base64Decode(event);
              _frames++;
              setState(() => _lastImage = bytes);
            } catch (e) {
              // 如果不是有效的 base64 圖片，當作一般文字處理
              _handleText(event);
            }
          } else if (event is List<int>) {
            // 如果收到二進制資料，直接使用
            final bytes = Uint8List.fromList(event);
            _frames++;
            setState(() => _lastImage = bytes);
          }
        },
        onDone: () {
          setState(() => _status = 'closed');
          _scheduleReconnect();
        },
        onError: (e, st) {
          setState(() => _status = 'error');
          _scheduleReconnect();
        },
        cancelOnError: true,
      );

      _heartbeatTimer = Timer.periodic(const Duration(seconds: 20), (_) {
        _sendJson({
          'type': 'ping',
          'ts': DateTime.now().millisecondsSinceEpoch,
        });
      });

      setState(() => _status = 'connected');
    } catch (e) {
      setState(() => _status = 'error');
      _scheduleReconnect();
    }
  }

  void _handleText(String text) {
    try {
      final obj = jsonDecode(text);
      if (obj is Map && obj['type'] == 'tick') {}
    } catch (_) {}
  }

  void _sendJson(Map<String, dynamic> obj) {
    _channel?.sink.add(jsonEncode(obj));
  }

  void _scheduleReconnect() {
    _heartbeatTimer?.cancel();
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), _connectWs);
  }

  void _cancelAll() {
    _heartbeatTimer?.cancel();
    _reconnectTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    _heartbeatTimer = null;
    _reconnectTimer = null;
    _sub = null;
    _channel = null;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      child: Stack(
        children: [
          // 背景影像
          Positioned.fill(
            child: _lastImage != null
                ? Image.memory(
                    _lastImage!,
                    gaplessPlayback: true,
                    fit: BoxFit.cover,
                  )
                : const Center(child: Text('等待 WebSocket 影像中…')),
          ),

          // 數據顯示面板（只保留一個）
          Positioned(
            bottom: 30,
            left: 120,
            right: 20,
            child: SizedBox(
              height: 250,
              child: Card(
                elevation: 3,
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: const DataDisplayPanel(
                    // 使用不同的 URL：圖片和數據分開
                    wsUrl: null, // 圖片已在上方處理，這裡不需要
                    dataUrl:
                        "ws://127.0.0.1:8080/stream/ws/data", // 修正 URL（移除雙斜線）
                    useFake: false,
                    angleWarnDeg: 5,
                    minDistM: 0.8,
                    maxDistM: 2.0,
                  ),
                ),
              ),
            ),
          ),

          // 可選：顯示連線狀態和 FPS 資訊
          Positioned(
            top: 20,
            right: 20,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(8.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _status == 'connected'
                              ? Icons.videocam
                              : Icons.videocam_off,
                          size: 16,
                          color: _status == 'connected'
                              ? Colors.green
                              : Colors.red,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '影像: $_status',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('FPS: $_fps', style: const TextStyle(fontSize: 12)),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class MapPage extends StatefulWidget {
  const MapPage({Key? key}) : super(key: key);

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  LatLng? userLocation;

  @override
  void initState() {
    super.initState();
    _getUserLocation();
  }

  Future<void> _getUserLocation() async {
    bool serviceEnabled;
    LocationPermission permission;

    // 檢查定位功能是否啟用
    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    // 檢查權限
    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.deniedForever ||
          permission == LocationPermission.denied) {
        return;
      }
    }

    Position position = await Geolocator.getCurrentPosition();
    setState(() {
      userLocation = LatLng(position.latitude, position.longitude);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (userLocation == null) {
      return Center(child: CircularProgressIndicator());
    }

    return Stack(
      children: [
        FlutterMap(
          options: MapOptions(initialCenter: userLocation!, initialZoom: 16.0),
          children: [
            TileLayer(
              urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
              subdomains: ['a', 'b', 'c'],
              userAgentPackageName: 'com.example.ipm',
            ),
            MarkerLayer(
              markers: [
                Marker(
                  point: userLocation!,
                  width: 40,
                  height: 40,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.blue,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 3),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
        Positioned(
          bottom: 30,
          left: 120,
          right: 20,
          child: Container(
            height: 80,
            color: Colors.white.withAlpha(230),
            child: Center(
              child: Text(
                "你目前的位置",
                style: TextStyle(fontSize: 18, color: Colors.grey[700]),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.account_circle, size: 250, color: Colors.grey[300]),
              ],
            ),
          ),
          const SizedBox(width: 20),
          Expanded(
            flex: 3,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                _InfoRow("用戶名稱", "王嘉成"),
                _InfoRow("租借站", "元智大學"),
                _InfoRow("卡片餘額", "NT\$ 999"),
                _InfoRow("騎乘時間", "25 分鐘"),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
          ),
          SizedBox(
            width: 350,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(value, style: const TextStyle(fontSize: 24)),
            ),
          ),
        ],
      ),
    );
  }
}
