import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import Constants from 'expo-constants';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'https://d7ae705b-7e8b-4812-a515-fa717748a941.preview.emergentagent.com';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

interface PlanPreview {
  date?: string;
  ageBand?: string;
  theme?: string;
  activities?: Array<{title: string; location?: string; duration?: string}>;
  fullPlanData?: any;  // Store full plan data from AI
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);
  const [user, setUser] = useState<any>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadUser();
    initializeChat();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        setUser(JSON.parse(userData));
      }
    } catch (error) {
      console.error('Error loading user:', error);
    }
  };

  const initializeChat = () => {
    const welcomeMessage: Message = {
      role: 'assistant',
      content: 'Merhaba! Ben MaarifPlanner AI Asistanınızım. Size Türkiye Yüzyılı Maarif Modeli ile uyumlu günlük ve aylık planlar oluşturmada yardımcı olabilirim.\n\nNasıl yardımcı olabilirim?',
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const token = await AsyncStorage.getItem('authToken');
      if (!token) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        router.replace('/auth/login');
        return;
      }

      const response = await fetch(`${BACKEND_URL}/api/ai/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputText.trim(),
          history: messages.slice(-10), // Last 10 messages for context
          ageBand: user?.ageDefault || '60_72',
          planType: 'daily',
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.message || 'Plan oluşturuldu!',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);

        // If a plan was generated, show preview
        if (data.finalize && data.planData) {
          setPlanPreview({
            date: data.planData.date || new Date().toISOString().split('T')[0],
            ageBand: data.planData.ageBand || '60_72',
            theme: data.planData.theme || 'AI Destekli Plan',
            activities: data.planData.activities?.slice(0, 3) || [],
            fullPlanData: data.planData  // Store full plan data for saving
          });
        }
        
      } else if (response.status === 401) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        router.replace('/auth/login');
      } else {
        const errorData = await response.json();
        const errorMessage: Message = {
          role: 'assistant',
          content: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const savePlan = async () => {
    if (!planPreview) return;

    try {
      const token = await AsyncStorage.getItem('authToken');
      if (!token) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        return;
      }

      // Get the full plan from the last AI response
      const lastAssistantMessage = messages.filter(m => m.role === 'assistant').pop();
      if (!lastAssistantMessage) return;

      const response = await fetch(`${BACKEND_URL}/api/plans/daily`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date: planPreview.date,
          ageBand: planPreview.ageBand,
          title: planPreview.theme || 'AI Destekli Günlük Plan',
          planJson: planPreview, // This should be the full plan data
        }),
      });

      if (response.ok) {
        const data = await response.json();
        Alert.alert('Başarılı', 'Plan kaydedildi!', [
          {
            text: 'Görüntüle',
            onPress: () => router.push(`/plan/${data.id}?type=daily`),
          },
          { text: 'Tamam', style: 'cancel' },
        ]);
        setPlanPreview(null);
      } else {
        Alert.alert('Hata', 'Plan kaydedilemedi');
      }
    } catch (error) {
      console.error('Save plan error:', error);
      Alert.alert('Hata', 'Bağlantı hatası');
    }
  };

  const renderMessage = (message: Message, index: number) => (
    <View
      key={index}
      style={[
        styles.messageContainer,
        message.role === 'user' ? styles.userMessage : styles.assistantMessage,
      ]}
    >
      <View style={[
        styles.messageBubble,
        message.role === 'user' ? styles.userBubble : styles.assistantBubble,
      ]}>
        <Text style={[
          styles.messageText,
          message.role === 'user' ? styles.userText : styles.assistantText,
        ]}>
          {message.content}
        </Text>
      </View>
    </View>
  );

  const renderPlanPreview = () => {
    if (!planPreview) return null;

    return (
      <View style={styles.planPreview}>
        <View style={styles.previewHeader}>
          <Ionicons name="document-text-outline" size={24} color="#3498db" />
          <Text style={styles.previewTitle}>Plan Önizleme</Text>
        </View>
        
        <View style={styles.previewContent}>
          <Text style={styles.previewInfo}>📅 Tarih: {planPreview.date}</Text>
          <Text style={styles.previewInfo}>👶 Yaş Grubu: {planPreview.ageBand}</Text>
          {planPreview.theme && (
            <Text style={styles.previewInfo}>🎯 Tema: {planPreview.theme}</Text>
          )}
          
          {planPreview.activities && planPreview.activities.length > 0 && (
            <View style={styles.activitiesPreview}>
              <Text style={styles.activitiesTitle}>🎨 Etkinlikler:</Text>
              {planPreview.activities.map((activity, index) => (
                <Text key={index} style={styles.activityItem}>
                  • {activity.title}
                </Text>
              ))}
            </View>
          )}
        </View>

        <View style={styles.previewActions}>
          <TouchableOpacity style={styles.discardButton} onPress={() => setPlanPreview(null)}>
            <Text style={styles.discardButtonText}>İptal</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveButton} onPress={savePlan}>
            <Text style={styles.saveButtonText}>Planı Kaydet</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>💬 AI Plan Asistanı</Text>
          {user && (
            <Text style={styles.subtitle}>Merhaba, {user.name}!</Text>
          )}
        </View>

        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map(renderMessage)}
          {isLoading && (
            <View style={[styles.messageContainer, styles.assistantMessage]}>
              <View style={[styles.messageBubble, styles.assistantBubble]}>
                <ActivityIndicator size="small" color="#7f8c8d" />
                <Text style={styles.loadingText}>AI düşünüyor...</Text>
              </View>
            </View>
          )}
        </ScrollView>

        {renderPlanPreview()}

        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            placeholder="Mesajınızı yazın..."
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={500}
            onSubmitEditing={sendMessage}
            blurOnSubmit={false}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.disabledSendButton]}
            onPress={sendMessage}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons 
              name="send" 
              size={20} 
              color={inputText.trim() && !isLoading ? '#fff' : '#bdc3c7'} 
            />
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 20,
  },
  messageContainer: {
    marginBottom: 15,
  },
  userMessage: {
    alignItems: 'flex-end',
  },
  assistantMessage: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '80%',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 18,
  },
  userBubble: {
    backgroundColor: '#3498db',
  },
  assistantBubble: {
    backgroundColor: '#fff',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  assistantText: {
    color: '#2c3e50',
  },
  loadingText: {
    marginLeft: 10,
    color: '#7f8c8d',
    fontSize: 14,
  },
  planPreview: {
    backgroundColor: '#fff',
    margin: 20,
    borderRadius: 10,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  previewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
  },
  previewTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2c3e50',
    marginLeft: 10,
  },
  previewContent: {
    padding: 15,
  },
  previewInfo: {
    fontSize: 14,
    color: '#2c3e50',
    marginBottom: 8,
  },
  activitiesPreview: {
    marginTop: 10,
  },
  activitiesTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 5,
  },
  activityItem: {
    fontSize: 13,
    color: '#7f8c8d',
    marginLeft: 10,
    marginBottom: 3,
  },
  previewActions: {
    flexDirection: 'row',
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#ecf0f1',
  },
  discardButton: {
    flex: 1,
    paddingVertical: 10,
    marginRight: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e74c3c',
    borderRadius: 8,
  },
  discardButtonText: {
    color: '#e74c3c',
    fontSize: 16,
    fontWeight: '500',
  },
  saveButton: {
    flex: 1,
    backgroundColor: '#27ae60',
    paddingVertical: 10,
    marginLeft: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 20,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
  },
  textInput: {
    flex: 1,
    backgroundColor: '#f1f2f6',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginRight: 10,
    maxHeight: 100,
    fontSize: 16,
    color: '#2c3e50',
  },
  sendButton: {
    backgroundColor: '#3498db',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledSendButton: {
    backgroundColor: '#ecf0f1',
  },
});