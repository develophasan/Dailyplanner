import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://plan-tester-1.preview.emergentagent.com';

interface MatrixItem {
  code: string;
  title: string;
  ageBand: string;
  description: string;
  area?: string;
}

export default function Matrix() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgeBand, setSelectedAgeBand] = useState('');
  const [searchResults, setSearchResults] = useState<MatrixItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    loadRecentSearches();
    // Load initial popular codes
    searchMatrix('');
  }, []);

  const loadRecentSearches = async () => {
    try {
      const searches = await AsyncStorage.getItem('recentMatrixSearches');
      if (searches) {
        setRecentSearches(JSON.parse(searches));
      }
    } catch (error) {
      console.error('Error loading recent searches:', error);
    }
  };

  const saveRecentSearch = async (query: string) => {
    if (!query.trim()) return;
    
    try {
      const newSearches = [query, ...recentSearches.filter(s => s !== query)].slice(0, 5);
      setRecentSearches(newSearches);
      await AsyncStorage.setItem('recentMatrixSearches', JSON.stringify(newSearches));
    } catch (error) {
      console.error('Error saving recent search:', error);
    }
  };

  const searchMatrix = async (query: string = searchQuery) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set('q', query.trim());
      if (selectedAgeBand) params.set('ageBand', selectedAgeBand);

      const response = await fetch(`${BACKEND_URL}/api/matrix/search?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Arama sonuçları yüklenemedi');
      }

      const results = await response.json();
      setSearchResults(results);
      
      if (query.trim()) {
        saveRecentSearch(query.trim());
      }
    } catch (error) {
      console.error('Matrix search error:', error);
      Alert.alert('Hata', 'Arama yapılırken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    searchMatrix();
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSelectedAgeBand('');
    searchMatrix('');
  };

  const selectRecentSearch = (query: string) => {
    setSearchQuery(query);
    searchMatrix(query);
  };

  const formatAgeBand = (ageBand: string) => {
    const ageMap: { [key: string]: string } = {
      '36_48': '36-48 Ay',
      '48_60': '48-60 Ay',
      '60_72': '60-72 Ay',
    };
    return ageMap[ageBand] || ageBand;
  };

  const getAreaFromCode = (code: string) => {
    if (code.startsWith('MAB')) return 'Matematik';
    if (code.startsWith('TADB')) return 'Türkçe';
    if (code.startsWith('HSAB')) return 'Fen';
    if (code.startsWith('SNAB')) return 'Sanat';
    if (code.startsWith('SDB')) return 'Sosyal';
    if (code.startsWith('MHB')) return 'Hareket ve Sağlık';
    if (code.startsWith('MÜZB')) return 'Müzik';
    return 'Diğer';
  };

  const getAreaColor = (area: string) => {
    const colors: { [key: string]: string } = {
      'Matematik': '#e74c3c',
      'Türkçe': '#3498db',
      'Fen': '#27ae60',
      'Sanat': '#f39c12',
      'Sosyal': '#9b59b6',
      'Hareket ve Sağlık': '#1abc9c',
      'Müzik': '#e67e22',
      'Diğer': '#95a5a6',
    };
    return colors[area] || '#95a5a6';
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Matrix & Kod Arama</Text>
      </View>

      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search-outline" size={20} color="#7f8c8d" />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Kod veya alan ara (örn: MAB.1, matematik...)"
            onSubmitEditing={handleSearch}
            returnKeyType="search"
          />
          {searchQuery ? (
            <TouchableOpacity onPress={clearSearch}>
              <Ionicons name="close-circle" size={20} color="#7f8c8d" />
            </TouchableOpacity>
          ) : null}
        </View>

        <View style={styles.filterContainer}>
          <Text style={styles.filterLabel}>Yaş Bandı:</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedAgeBand}
              onValueChange={setSelectedAgeBand}
              style={styles.picker}
            >
              <Picker.Item label="Tüm Yaşlar" value="" />
              <Picker.Item label="36-48 Ay" value="36_48" />
              <Picker.Item label="48-60 Ay" value="48_60" />
              <Picker.Item label="60-72 Ay" value="60_72" />
            </Picker>
          </View>
        </View>

        <TouchableOpacity 
          style={styles.searchButton} 
          onPress={handleSearch}
          disabled={isLoading}
        >
          <Ionicons name="search" size={20} color="white" />
          <Text style={styles.searchButtonText}>
            {isLoading ? 'Aranıyor...' : 'Ara'}
          </Text>
        </TouchableOpacity>
      </View>

      {recentSearches.length > 0 && !searchQuery && (
        <View style={styles.recentContainer}>
          <Text style={styles.recentTitle}>Son Aramalar:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.recentTags}>
              {recentSearches.map((search, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.recentTag}
                  onPress={() => selectRecentSearch(search)}
                >
                  <Text style={styles.recentTagText}>{search}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>
        </View>
      )}

      <ScrollView style={styles.resultsContainer}>
        {searchResults.length === 0 && !isLoading ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="search-outline" size={64} color="#bdc3c7" />
            <Text style={styles.emptyTitle}>Sonuç bulunamadı</Text>
            <Text style={styles.emptySubtitle}>
              Farklı anahtar kelimeler deneyin veya yaş bandı filtresini değiştirin
            </Text>
          </View>
        ) : (
          <View style={styles.resultsList}>
            {searchResults.map((item, index) => {
              const area = getAreaFromCode(item.code);
              const areaColor = getAreaColor(area);
              
              return (
                <View key={index} style={styles.resultCard}>
                  <View style={styles.resultHeader}>
                    <View style={styles.codeContainer}>
                      <Text style={styles.resultCode}>{item.code}</Text>
                      <View style={[styles.areaTag, { backgroundColor: areaColor }]}>
                        <Text style={styles.areaTagText}>{area}</Text>
                      </View>
                    </View>
                    <Text style={styles.resultAgeBand}>
                      {formatAgeBand(item.ageBand)}
                    </Text>
                  </View>
                  
                  <Text style={styles.resultTitle}>{item.title}</Text>
                  <Text style={styles.resultDescription}>{item.description}</Text>
                  
                  <View style={styles.resultActions}>
                    <TouchableOpacity style={styles.actionButton}>
                      <Ionicons name="add-circle-outline" size={18} color="#3498db" />
                      <Text style={styles.actionButtonText}>Plana Ekle</Text>
                    </TouchableOpacity>
                    
                    <TouchableOpacity style={styles.actionButton}>
                      <Ionicons name="bookmark-outline" size={18} color="#f39c12" />
                      <Text style={styles.actionButtonText}>Kaydet</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
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
  searchContainer: {
    backgroundColor: 'white',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  searchInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    marginLeft: 8,
    color: '#2c3e50',
  },
  filterContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  filterLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2c3e50',
    marginRight: 12,
  },
  pickerContainer: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
  },
  picker: {
    height: 40,
  },
  searchButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#3498db',
    borderRadius: 8,
    paddingVertical: 12,
  },
  searchButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  recentContainer: {
    backgroundColor: 'white',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  recentTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#7f8c8d',
    marginBottom: 8,
  },
  recentTags: {
    flexDirection: 'row',
  },
  recentTag: {
    backgroundColor: '#f8f9fa',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  recentTagText: {
    fontSize: 14,
    color: '#3498db',
  },
  resultsContainer: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 22,
  },
  resultsList: {
    padding: 16,
  },
  resultCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  codeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  resultCode: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginRight: 8,
  },
  areaTag: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  areaTagText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  resultAgeBand: {
    backgroundColor: '#ecf0f1',
    color: '#2c3e50',
    fontSize: 12,
    fontWeight: 'bold',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
  resultDescription: {
    fontSize: 14,
    color: '#7f8c8d',
    lineHeight: 20,
    marginBottom: 12,
  },
  resultActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    paddingVertical: 8,
    marginHorizontal: 4,
    borderRadius: 6,
    backgroundColor: '#f8f9fa',
  },
  actionButtonText: {
    fontSize: 14,
    color: '#3498db',
    marginLeft: 4,
    fontWeight: '500',
  },
});