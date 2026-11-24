/// The signed-in session: who is using the app, in which language, against which server.
library;

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api.dart';
import 'models.dart';

/// Where the app keeps its few saved values (token, server address, language).
abstract class KeyValueStore {
  Future<String?> read(String key);
  Future<void> write(String key, String? value);
}

/// Real devices: the platform's encrypted storage (Keychain on iOS, Keystore on Android).
class SecureStore implements KeyValueStore {
  const SecureStore();
  static const _storage = FlutterSecureStorage();

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String? value) =>
      value == null ? _storage.delete(key: key) : _storage.write(key: key, value: value);
}

/// Tests: plain memory.
class MemoryStore implements KeyValueStore {
  final Map<String, String> values = {};

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String? value) async => value == null ? values.remove(key) : values[key] = value;
}

/// Address used until the user enters another one on the sign-in screen.
/// 10.0.2.2 is how the Android emulator reaches the computer it runs on.
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

  /// False until [restore] has finished, so the app can show a splash instead of the sign-in form.
  bool ready = false;

  String get language => _language;
  String get serverUrl => api.baseUrl;
  bool get isSignedIn => user != null;

  /// Called once at start-up: reuse the saved token if the server still accepts it.
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
        // An expired or revoked token is forgotten; with no network we keep it and let the user retry.
        if (error.isUnauthorized) {
          api.token = null;
          await store.write('token', null);
        }
      }
    }
    ready = true;
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
