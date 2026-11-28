library;

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api.dart';
import 'models.dart';

abstract class KeyValueStore {
  Future<String?> read(String key);
  Future<void> write(String key, String? value);
}

class SecureStore implements KeyValueStore {
  const SecureStore();
  static const _storage = FlutterSecureStorage();

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String? value) =>
      value == null ? _storage.delete(key: key) : _storage.write(key: key, value: value);
}

class MemoryStore implements KeyValueStore {
  final Map<String, String> values = {};

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String? value) async => value == null ? values.remove(key) : values[key] = value;
}

/// Override at build time:  flutter run --dart-define=API_URL=http://192.168.1.20:8000
const defaultServerUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');

const supportedLanguages = ['kk', 'ru', 'en'];

class Session extends ChangeNotifier {
  Session({required this.store, ApiClient? api, String? deviceLanguage})
    : api = api ?? ApiClient(baseUrl: defaultServerUrl),
      _language = supportedLanguages.contains(deviceLanguage) ? deviceLanguage! : 'ru';

  final KeyValueStore store;
  final ApiClient api;

  AppUser? user;
  String _language;

  bool ready = false;

  String get language => _language;
  String get serverUrl => api.baseUrl;
  bool get isSignedIn => user != null;

  Future<void> restore() async {
    final savedUrl = await store.read('server_url');
    if (savedUrl != null && savedUrl.isNotEmpty) api.baseUrl = savedUrl;
    final savedLanguage = await store.read('language');
    if (supportedLanguages.contains(savedLanguage)) _language = savedLanguage!;
    final token = await store.read('token');
    if (token != null) {
      api.token = token;
      try {
        user = await api.me();
      } on ApiException catch (error) {
        if (error.isUnauthorized) {
          api.token = null;
          await store.write('token', null);
        }
      }
    }
    ready = true;
    notifyListeners();
  }

  Future<void> setServerUrl(String value) async {
    final url = ApiClient.normalizeBaseUrl(value);
    if (url.isEmpty || url == api.baseUrl) return;
    api.baseUrl = url;
    await store.write('server_url', url);
    notifyListeners();
  }

  Future<void> signIn(String email, String password, {String? serverUrl}) async {
    if (serverUrl != null && serverUrl.trim().isNotEmpty) {
      api.baseUrl = ApiClient.normalizeBaseUrl(serverUrl);
      await store.write('server_url', api.baseUrl);
    }
    user = await api.login(email, password);
    await store.write('token', api.token);
    notifyListeners();
  }

  Future<void> register({required String name, required String email, required String password}) async {
    await api.register(name: name, email: email, password: password, language: _language);
    await signIn(email, password);
  }

  Future<void> signOut() async {
    api.token = null;
    user = null;
    await store.write('token', null);
    notifyListeners();
  }

  Future<void> setLanguage(String code) async {
    if (!supportedLanguages.contains(code) || code == _language) return;
    _language = code;
    await store.write('language', code);
    notifyListeners();
  }
}
