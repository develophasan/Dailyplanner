import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://dailyplanner-8.preview.emergentagent.com';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AIResponse {
  finalize: boolean;
  type: 'daily' | 'monthly';
  ageBand: string;
  date?: string;
  domainOutcomes?: any[];
  blocks?: any;
  followUpQuestions?: string[];
  missingFields?: string[];
  notes?: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [currentResponse, setCurrentResponse] = useState<AIResponse | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadUser();
    // Add welcome message
    setMessages([{
      role: 'assistant',
      content: 'Merhaba! Ben MaarifPlanner AI asistanınızım. Günlük veya aylık plan oluşturmanızda size yardımcı olacağım. Hangi yaş bandı için plan oluşturmak istiyorsunuz ve ne tür etkinlikler planlıyorsunuz?',
      timestamp: new Date().toISOString(),
    }]);
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

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const token = await getAuthToken();
      if (!token) {
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
          history: messages,
          ageBand: user?.ageDefault || '60_72',
          planType: 'daily',
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          router.replace('/auth/login');
          return;
        }
        throw new Error('AI yanıt verirken hata oluştu');
      }

      const aiResponse: AIResponse = await response.json();
      setCurrentResponse(aiResponse);

      let responseText = '';
      
      if (aiResponse.finalize) {
        responseText = 'Harika! Planınız hazır. Size bir önizleme göstereyim:\n\n';
        
        if (aiResponse.domainOutcomes && aiResponse.domainOutcomes.length > 0) {
          responseText += '📋 **Hedeflenen Alanlar:**\n';
          aiResponse.domainOutcomes.forEach(outcome => {
            responseText += `• ${outcome.code}\n`;
          });
          responseText += '\n';
        }

        if (aiResponse.blocks?.activities && aiResponse.blocks.activities.length > 0) {
          responseText += '🎯 **Etkinlikler:**\n';
          aiResponse.blocks.activities.forEach((activity: any, index: number) => {
            responseText += `${index + 1}. ${activity.title}\n`;
          });
          responseText += '\n';
        }

        responseText += 'Planı kaydetmek ve PDF olarak indirmek ister misiniz?';
      } else {
        responseText = 'Planınızı tamamlamak için birkaç ek bilgiye ihtiyacım var:\n\n';
        
        if (aiResponse.followUpQuestions && aiResponse.followUpQuestions.length > 0) {
          aiResponse.followUpQuestions.forEach((question, index) => {
            responseText += `${index + 1}. ${question}\n`;
          });
        }
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      Alert.alert('Hata', 'Mesaj gönderilirken hata oluştu. Lütfen tekrar deneyin.');
      
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const savePlan = async () => {
    if (!currentResponse || !currentResponse.finalize) return;

    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      const response = await fetch(`${BACKEND_URL}/api/plans/daily`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date: currentResponse.date || new Date().toISOString().split('T')[0],
          ageBand: currentResponse.ageBand,
          planJson: currentResponse,
          title: `${currentResponse.type === 'daily' ? 'Günlük' : 'Aylık'} Plan - ${currentResponse.date}`,
        }),
      });

      if (response.ok) {
        Alert.alert('Başarılı', 'Plan kaydedildi!', [
          {
            text: 'Planları Görüntüle',
            onPress: () => router.push('/(tabs)/plans'),
          },
          {
            text: 'Yeni Plan',
            onPress: () => {
              setMessages([{
                role: 'assistant',
                content: 'Yeni bir plan oluşturmak için ne yapmak istiyorsunuz?',
                timestamp: new Date().toISOString(),
              }]);
              setCurrentResponse(null);
            },
          },
        ]);
      } else {
        throw new Error('Plan kaydedilemedi');
      }
    } catch (error) {
      console.error('Save plan error:', error);
      Alert.alert('Hata', 'Plan kaydedilirken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    Alert.alert(
      'Sohbeti Temizle',
      'Tüm sohbet geçmişi silinecek. Emin misiniz?',
      [
        { text: 'İptal', style: 'cancel' },
        {
          text: 'Temizle',
          style: 'destructive',
          onPress: () => {
            setMessages([{
              role: 'assistant',
              content: 'Merhaba! Ben MaarifPlanner AI asistanınızım. Günlük veya aylık plan oluşturmanızda size yardımcı olacağım. Hangi yaş bandı için plan oluşturmak istiyorsunuz ve ne tür etkinlikler planlıyorsunuz?',
              timestamp: new Date().toISOString(),
            }]);
            setCurrentResponse(null);
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Plan Asistanı</Text>
        <TouchableOpacity onPress={clearChat} style={styles.clearButton}>
          <Ionicons name="refresh-outline" size={24} color="#3498db" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.chatContainer}
      >
        <ScrollView 
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((message, index) => (
            <View key={index} style={[
              styles.messageContainer,
              message.role === 'user' ? styles.userMessage : styles.assistantMessage
            ]}>
              <Text style={[
                styles.messageText,
                message.role === 'user' ? styles.userMessageText : styles.assistantMessageText
              ]}>
                {message.content}
              </Text>
              <Text style={styles.messageTime}>
                {new Date(message.timestamp).toLocaleTimeString('tr-TR', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
            </View>
          ))}
          
          {isLoading && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="small" color="#3498db" />
              <Text style={styles.loadingText}>AI yanıt hazırlıyor...</Text>
            </View>
          )}
        </ScrollView>

        {currentResponse?.finalize && (
          <View style={styles.actionContainer}>
            <TouchableOpacity 
              style={styles.saveButton}
              onPress={savePlan}
              disabled={isLoading}
            >
              <Ionicons name="save-outline" size={20} color="white" />
              <Text style={styles.saveButtonText}>Planı Kaydet</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Mesajınızı yazın..."
            multiline
            maxLength={1000}
            onSubmitEditing={sendMessage}
          />
          <TouchableOpacity 
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.disabledButton]}
            onPress={sendMessage}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons name="send" size={20} color="white" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  clearButton: {
    padding: 4,
  },
  chatContainer: {
    flex: 1,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 8,
  },
  messageContainer: {
    marginBottom: 16,
    maxWidth: '80%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#3498db',
    borderRadius: 16,
    padding: 12,
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: 'white',
  },
  assistantMessageText: {
    color: '#2c3e50',
  },
  messageTime: {
    fontSize: 12,
    color: '#7f8c8d',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    marginBottom: 16,
  },
  loadingText: {
    marginLeft: 8,
    color: '#7f8c8d',
    fontSize: 14,
  },
  actionContainer: {
    padding: 16,
    paddingTop: 8,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#27ae60',
    borderRadius: 8,
    padding: 12,
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
    alignItems: 'flex-end',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    maxHeight: 100,
    marginRight: 8,
  },
  sendButton: {
    backgroundColor: '#3498db',
    borderRadius: 20,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
  },
});