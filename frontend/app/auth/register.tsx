import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function RegisterScreen() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    school: '',
    className: '',
    ageDefault: '60_72',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async () => {
    const { name, email, password, confirmPassword, school, className, ageDefault } = formData;

    if (!name || !email || !password) {
      if (Platform.OS === 'web') {
        alert('Ad, e-posta ve şifre gereklidir.');
      } else {
        Alert.alert('Hata', 'Ad, e-posta ve şifre gereklidir.');
      }
      return;
    }

    if (password !== confirmPassword) {
      if (Platform.OS === 'web') {
        alert('Şifreler eşleşmiyor.');
      } else {
        Alert.alert('Hata', 'Şifreler eşleşmiyor.');
      }
      return;
    }

    if (password.length < 6) {
      if (Platform.OS === 'web') {
        alert('Şifre en az 6 karakter olmalıdır.');
      } else {
        Alert.alert('Hata', 'Şifre en az 6 karakter olmalıdır.');
      }
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.toLowerCase().trim(),
          password,
          school: school.trim() || null,
          className: className.trim() || null,
          ageDefault,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Save token
        await AsyncStorage.setItem('authToken', data.token);
        await AsyncStorage.setItem('user', JSON.stringify(data.user));
        
        if (Platform.OS === 'web') {
          alert('Hesap oluşturuldu!');
          router.replace('/(tabs)/chat');
        } else {
          Alert.alert('Başarılı', 'Hesap oluşturuldu!', [
            {
              text: 'Tamam',
              onPress: () => router.replace('/(tabs)/chat'),
            },
          ]);
        }
      } else {
        if (Platform.OS === 'web') {
          alert(data.detail || 'Kayıt başarısız');
        } else {
          Alert.alert('Hata', data.detail || 'Kayıt başarısız');
        }
      }
    } catch (error) {
      console.error('Register error:', error);
      if (Platform.OS === 'web') {
        alert('Bağlantı hatası. Lütfen tekrar deneyin.');
      } else {
        Alert.alert('Hata', 'Bağlantı hatası. Lütfen tekrar deneyin.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const updateFormData = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#2c3e50" />
            </TouchableOpacity>
            <Text style={styles.title}>Kayıt Ol</Text>
            <Text style={styles.subtitle}>Hesap oluşturun</Text>
          </View>

          <View style={styles.form}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Ad ve Soyad</Text>
              <TextInput
                style={styles.input}
                placeholder="Adınızı ve soyadınızı girin"
                value={formData.name}
                onChangeText={(value) => updateFormData('name', value)}
                autoCapitalize="words"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={styles.input}
                placeholder="ornek@email.com"
                value={formData.email}
                onChangeText={(value) => updateFormData('email', value)}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Şifre</Text>
              <TextInput
                style={styles.input}
                placeholder="En az 6 karakter"
                value={formData.password}
                onChangeText={(value) => updateFormData('password', value)}
                secureTextEntry
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Şifre Tekrar</Text>
              <TextInput
                style={styles.input}
                placeholder="Şifrenizi tekrar girin"
                value={formData.confirmPassword}
                onChangeText={(value) => updateFormData('confirmPassword', value)}
                secureTextEntry
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Okul (isteğe bağlı)</Text>
              <TextInput
                style={styles.input}
                placeholder="Okulunuzun adı (isteğe bağlı)"
                value={formData.school}
                onChangeText={(value) => updateFormData('school', value)}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Sınıf (isteğe bağlı)</Text>
              <TextInput
                style={styles.input}
                placeholder="Sınıf adı (isteğe bağlı)"
                value={formData.className}
                onChangeText={(value) => updateFormData('className', value)}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Varsayılan Yaş Grubu</Text>
              <View style={styles.pickerContainer}>
                <Picker
                  selectedValue={formData.ageDefault}
                  onValueChange={(value) => updateFormData('ageDefault', value)}
                  style={styles.picker}
                >
                  <Picker.Item label="36-48 Ay" value="36_48" />
                  <Picker.Item label="48-60 Ay" value="48_60" />
                  <Picker.Item label="60-72 Ay" value="60_72" />
                </Picker>
              </View>
            </View>

            <Pressable 
              style={[styles.registerButton, isLoading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={isLoading}
              accessibilityRole="button"
            >
              <Text style={styles.registerButtonText}>
                {isLoading ? 'Kayıt yapılıyor...' : 'Kayıt Ol'}
              </Text>
            </Pressable>
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerText}>Zaten hesabınız var mı? </Text>
            <TouchableOpacity onPress={() => router.push('/auth/login')}>
              <Text style={styles.footerLink}>Giriş Yap</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
  },
  backButton: {
    position: 'absolute',
    left: 0,
    top: 0,
    padding: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
  },
  form: {
    flex: 1,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#fff',
    paddingVertical: 15,
    paddingHorizontal: 20,
    borderRadius: 10,
    fontSize: 16,
    color: '#2c3e50',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  pickerContainer: {
    backgroundColor: '#fff',
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  picker: {
    height: 50,
  },
  registerButton: {
    backgroundColor: '#27ae60',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  disabledButton: {
    backgroundColor: '#95a5a6',
  },
  registerButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 30,
  },
  footerText: {
    fontSize: 16,
    color: '#7f8c8d',
  },
  footerLink: {
    fontSize: 16,
    color: '#3498db',
    fontWeight: '500',
  },
});